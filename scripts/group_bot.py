#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Group @-reply bot using wx4py process_groups + optional domestic AI."""

from __future__ import annotations

import argparse
import logging
import os
import sys
from pathlib import Path

from wx4py import AsyncCallbackHandler, CallbackHandler, MessageEvent, WeChatClient

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wx4py_mcp.config import Wx4PyConfig
from wx4py_mcp.filters import MessageFilter, parse_keywords

logger = logging.getLogger(__name__)


def main() -> None:
    parser = argparse.ArgumentParser(description="Group listener with keyword / @ filter")
    parser.add_argument("--groups", required=True, help="Comma-separated group names")
    parser.add_argument("--keywords", default="", help="Optional keyword filter")
    parser.add_argument("--reply-on-at", action="store_true", default=True)
    parser.add_argument("--reply", default="", help="Fixed reply; empty = echo prefix")
    parser.add_argument("--ai", action="store_true", help="Use WX4PY_AI_* env")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    groups = [g.strip() for g in args.groups.split(",") if g.strip()]
    msg_filter = MessageFilter(
        keywords=parse_keywords(args.keywords),
        reply_on_at=args.reply_on_at,
    )
    cfg = Wx4PyConfig.from_env()
    ai_client = None
    if args.ai:
        if not cfg.ai_base_url or not cfg.ai_api_key:
            logger.error("AI mode requires WX4PY_AI_BASE_URL and WX4PY_AI_API_KEY")
            sys.exit(1)
        from wx4py import AIClient, AIConfig

        ai_client = AIClient(
            AIConfig(
                base_url=cfg.ai_base_url,
                model=cfg.ai_model,
                api_key=cfg.ai_api_key,
                api_format=cfg.ai_api_format,
            )
        )

    def on_message(event: MessageEvent) -> str:
        msg_filter.is_at_me = event.is_at_me
        if not msg_filter.match(event.content):
            return ""
        if ai_client:
            return ai_client.chat([{"role": "user", "content": event.content}])
        if args.reply:
            return args.reply
        return f"收到：{event.content}"

    handler = AsyncCallbackHandler(on_message, auto_reply=True, reply_on_at=args.reply_on_at)
    logger.info("Listening groups: %s", groups)
    with WeChatClient(auto_connect=True) as wx:
        wx.process_groups(groups, [handler], block=True)


if __name__ == "__main__":
    main()
