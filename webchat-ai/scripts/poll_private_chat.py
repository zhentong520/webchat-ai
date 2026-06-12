#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Private chat polling listener (wxauto-mcp api_listen pattern, wx4py backend).

MCP cannot block forever; run this as a standalone process for 1:1 auto-reply.

Examples:
  python poll_private_chat.py --contacts Air,娟子 --interval 15
  python poll_private_chat.py --contacts Air --keywords 在吗,你好 --reply "在的，稍后回复"
  set WX4PY_AI_BASE_URL=... && set WX4PY_AI_API_KEY=... && python poll_private_chat.py --contacts Air --ai
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path
from typing import Callable, Optional

from wx4py import WeChatClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wx4py_mcp.config import Wx4PyConfig
from wx4py_mcp.filters import MessageFilter, parse_keywords
from wx4py_mcp.listen_handlers import process_targets_once, resume_targets_on_start, run_startup_catchup
from wx4py_mcp.state_store import DEFAULT_STATE_FILE
from wx4py_mcp.state_store import load_state as read_state
from wx4py_mcp.state_store import save_state as write_state
from wx4py_mcp.workbuddy_model import PRIVATE_SYSTEM_PROMPT, clean_reply_text, resolve_workbuddy_model

logger = logging.getLogger(__name__)
STATE_FILE = Path(os.getenv("WX4PY_STATE_DIR", str(DEFAULT_STATE_FILE.parent))) / "private_seen.json"
if not os.getenv("WX4PY_STATE_DIR"):
    STATE_FILE = DEFAULT_STATE_FILE
OUTGOING_SUFFIX = "__outgoing"
LAST_REPLIED_SUFFIX = "__last_replied__"
TARGET_TYPE = "contact"


def outgoing_key(contact: str) -> str:
    return f"{contact}{OUTGOING_SUFFIX}"


def last_replied_key(contact: str) -> str:
    return f"{contact}{LAST_REPLIED_SUFFIX}"


def load_outgoing(state: dict[str, list[str]], contact: str) -> set[str]:
    return set(state.get(outgoing_key(contact), []))


def record_outgoing(state: dict[str, list[str]], contact: str, text: str) -> None:
    items = state.setdefault(outgoing_key(contact), [])
    items.append(text)
    state[outgoing_key(contact)] = items[-100:]


def build_ai_reply(cfg: Wx4PyConfig, workbuddy: bool = False) -> Optional[Callable[[str, str], str]]:
    from wx4py import AIClient, AIConfig

    if workbuddy:
        resolved = resolve_workbuddy_model()
        client = AIClient(
            AIConfig(
                base_url=resolved.base_url,
                model=resolved.model,
                api_key=resolved.api_key,
                api_format=resolved.api_format,
                system_prompt=PRIVATE_SYSTEM_PROMPT,
                enable_thinking=False,
            )
        )
        logger.info("AI via %s model=%s", resolved.source, resolved.model)
    else:
        if not cfg.ai_base_url or not cfg.ai_api_key:
            return None
        client = AIClient(
            AIConfig(
                base_url=cfg.ai_base_url,
                model=cfg.ai_model,
                api_key=cfg.ai_api_key,
                api_format=cfg.ai_api_format,
                system_prompt=PRIVATE_SYSTEM_PROMPT,
                enable_thinking=False,
            )
        )

    def _reply(contact: str, content: str) -> str:
        from wx4py_mcp.conversation_memory import append_exchange, build_messages_with_memory, is_memory_enabled

        api_messages = build_messages_with_memory(contact, TARGET_TYPE, content)
        raw = client.chat(api_messages, system_prompt=PRIVATE_SYSTEM_PROMPT)
        reply = clean_reply_text(raw)
        if is_memory_enabled() and reply:
            append_exchange(contact, TARGET_TYPE, content, reply)
        return reply

    return _reply


def _handler_kwargs() -> dict:
    return {
        "last_replied_key_fn": last_replied_key,
        "outgoing_key_fn": outgoing_key,
        "load_outgoing_fn": load_outgoing,
        "record_outgoing_fn": record_outgoing,
        "enable_calls": True,
    }


def poll_once(
    wx: WeChatClient,
    contacts: list[str],
    state: dict[str, list[str]],
    msg_filter: MessageFilter,
    fixed_reply: str,
    ai_reply: Optional[Callable[[str, str], str]],
    echo_reply: bool = False,
) -> tuple[int, bool]:
    return process_targets_once(
        wx,
        contacts,
        TARGET_TYPE,
        state,
        msg_filter,
        fixed_reply,
        ai_reply,
        echo_reply,
        phase="poll",
        **_handler_kwargs(),
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="Poll private WeChat chats and auto-reply")
    parser.add_argument("--contacts", required=True, help="Comma-separated remark names, e.g. Air,娟子")
    parser.add_argument("--interval", type=float, default=15.0, help="Poll interval seconds")
    parser.add_argument("--keywords", default="", help="Only reply when message contains keywords")
    parser.add_argument("--exclude", default="", help="Skip messages containing these keywords")
    parser.add_argument("--reply", default="", help="Fixed reply text")
    parser.add_argument("--echo", action="store_true", help="Reply with 收到：<their message> (no AI)")
    parser.add_argument("--ai", action="store_true", help="Use WX4PY_AI_* env for reply")
    parser.add_argument(
        "--workbuddy",
        action="store_true",
        help="Use WorkBuddy/mmx/OpenClaw model on this machine (default when no --echo)",
    )
    parser.add_argument("--once", action="store_true", help="Run one poll cycle and exit")
    parser.add_argument(
        "--no-startup-catchup",
        action="store_true",
        help="Skip startup last-message check (default: catch up on boot)",
    )
    args = parser.parse_args()

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    logging.getLogger("wx4py_mcp.open_chat").setLevel(logging.INFO)
    logging.getLogger("wx4py_mcp.last_message").setLevel(logging.INFO)
    cfg = Wx4PyConfig.from_env()
    contacts = [c.strip() for c in args.contacts.split(",") if c.strip()]
    msg_filter = MessageFilter(
        keywords=parse_keywords(args.keywords),
        exclude_keywords=parse_keywords(args.exclude),
    )
    ai_reply = None
    use_workbuddy = args.workbuddy or (not args.echo and not args.ai)
    if args.ai:
        ai_reply = build_ai_reply(cfg, workbuddy=False)
        if not ai_reply:
            logger.error("AI mode requires WX4PY_AI_BASE_URL and WX4PY_AI_API_KEY")
            sys.exit(1)
    elif use_workbuddy:
        try:
            ai_reply = build_ai_reply(cfg, workbuddy=True)
        except RuntimeError as exc:
            logger.error("%s", exc)
            sys.exit(1)

    state = read_state(STATE_FILE)
    resume_targets_on_start(state, contacts)
    write_state(state, STATE_FILE)

    logger.info("Polling contacts: %s every %ss", contacts, args.interval)

    with WeChatClient() as wx:
        if not args.no_startup_catchup and not args.once:
            count, should_exit = run_startup_catchup(
                wx,
                contacts,
                TARGET_TYPE,
                state,
                msg_filter,
                args.reply,
                ai_reply,
                args.echo,
                **_handler_kwargs(),
            )
            write_state(state, STATE_FILE)
            if count:
                logger.info("[startup] handled %s pending reply(ies)", count)
            if should_exit:
                logger.info("Stop command on startup, listener exiting.")
                return

        while True:
            count, should_exit = poll_once(
                wx, contacts, state, msg_filter, args.reply, ai_reply, args.echo
            )
            write_state(state, STATE_FILE)
            if count:
                logger.info("Handled %s replies this cycle", count)
            if should_exit:
                logger.info("Stop command received, listener exiting.")
                break
            if args.once:
                break
            time.sleep(args.interval)


if __name__ == "__main__":
    main()
