"""Shared listen loop: startup catch-up + poll cycle."""

from __future__ import annotations

import logging
from typing import Any, Callable, Optional

from wx4py_mcp.listen_control import (
    ACK_CALL_FAIL,
    ACK_START,
    ACK_STOP,
    ACK_VIDEO_CALL,
    ACK_VOICE_CALL,
    is_paused,
    match_call_command,
    match_control_command,
    set_paused,
)
from wx4py_mcp.last_message import get_last_chat_line
from wx4py_mcp.open_chat import send_message_smart
from wx4py_mcp.wechat_reconnect import ensure_wechat_connected

logger = logging.getLogger(__name__)


def pick_pending_peer_message(
    last_msg: Optional[dict[str, Any]],
    already_replied_key: str,
    outgoing: Optional[set[str]] = None,
) -> Optional[tuple[str, str]]:
    """Reply when the last visible line is from peer (left/grey bubble)."""
    if not last_msg:
        return None
    if (last_msg.get("type") or "text") == "system":
        return None

    content = (last_msg.get("content") or "").strip()
    if not content:
        msg_type = last_msg.get("type") or ""
        if msg_type in ("voice", "image", "document"):
            logger.info("skip: %s message not resolved yet", msg_type)
        return None

    if not last_msg.get("from_peer", False):
        logger.debug("skip: last line is on the right (self/green)")
        return None

    if outgoing and content in outgoing:
        logger.info("skip: last line matches our outgoing message")
        return None

    from wx4py_mcp.voice_message import voice_message_key

    msg_type = last_msg.get("type") or ""
    if msg_type == "voice":
        key = voice_message_key(last_msg)
    elif msg_type == "image":
        from wx4py_mcp.image_message import image_message_key

        key = image_message_key(last_msg)
    elif msg_type == "document":
        from wx4py_mcp.document_message import document_message_key

        key = document_message_key(last_msg)
    else:
        key = f"{last_msg.get('time', '')}|{content}"

    if key == already_replied_key:
        logger.debug("skip: already handled this last peer line")
        return None

    return key, content


def resume_targets_on_start(state: dict[str, Any], targets: list[str]) -> None:
    """Starting listener implies resume — clear paused flags."""
    for name in targets:
        if is_paused(state, name):
            logger.info("[startup] resume %s (was paused)", name)
            set_paused(state, name, False)


def process_targets_once(
    wx,
    targets: list[str],
    target_type: str,
    state: dict[str, Any],
    msg_filter,
    fixed_reply: str,
    ai_reply: Optional[Callable[[str, str], str]],
    echo_reply: bool,
    *,
    last_replied_key_fn: Callable[[str], str],
    outgoing_key_fn: Callable[[str], str],
    load_outgoing_fn: Callable[[dict, str], set[str]],
    record_outgoing_fn: Callable[[dict, str, str], None],
    enable_calls: bool = False,
    phase: str = "poll",
) -> tuple[int, bool]:
    """
    Read last visible message per target; recognize voice/image; reply if peer pending.

    phase='startup' logs explicitly for listener boot catch-up.
    """
    handled = 0
    should_exit = False
    try:
        wx = ensure_wechat_connected(wx)
    except Exception as exc:
        logger.warning("WeChat not available this cycle: %s", exc)
        return handled, should_exit

    for target in targets:
        if phase == "startup":
            logger.info("[startup] check last message: %s", target)
        try:
            last_msg = get_last_chat_line(wx.chat_window, target, target_type)
        except Exception as exc:
            logger.warning("last message failed for %s: %s", target, exc)
            continue

        if phase == "startup" and last_msg:
            msg_type = last_msg.get("type") or "text"
            side = "peer" if last_msg.get("from_peer") else "self"
            preview = (last_msg.get("content") or last_msg.get("raw_name") or "")[:80]
            logger.info("[startup] %s last=%s side=%s preview=%s", target, msg_type, side, preview)

        already_replied = state.get(last_replied_key_fn(target), "")
        outgoing = load_outgoing_fn(state, target)
        pending = pick_pending_peer_message(last_msg, already_replied, outgoing)
        if not pending:
            if phase == "startup":
                logger.info("[startup] %s nothing to reply", target)
            continue

        key, content = pending
        msg_type = (last_msg or {}).get("type") or "text"
        control = match_control_command(content)
        call_type = match_call_command(content) if enable_calls else None

        if control == "stop":
            set_paused(state, target, True)
            reply_text = ACK_STOP
            should_exit = True
        elif control == "start":
            set_paused(state, target, False)
            reply_text = ACK_START
        elif call_type == "video" and enable_calls:
            from wx4py_mcp.call_control import start_video_call

            logger.info("[%s] peer requested video call", target)
            ok = start_video_call(wx.chat_window, target, target_type)
            reply_text = ACK_VIDEO_CALL if ok else ACK_CALL_FAIL
        elif call_type == "voice" and enable_calls:
            from wx4py_mcp.call_control import start_voice_call

            logger.info("[%s] peer requested voice call", target)
            ok = start_voice_call(wx.chat_window, target, target_type)
            reply_text = ACK_VOICE_CALL if ok else ACK_CALL_FAIL
        elif is_paused(state, target):
            state[last_replied_key_fn(target)] = key
            logger.info("[%s] paused, ignore peer: %s", target, content[:60])
            continue
        elif not msg_filter.match(content):
            logger.debug("[%s] skip filtered: %s", target, content[:60])
            continue
        elif msg_type in ("image", "document"):
            reply_text = content
            logger.info("[%s] direct media reply (%s)", target, msg_type)
        elif fixed_reply:
            reply_text = fixed_reply
        elif echo_reply:
            reply_text = f"收到：{content}"
        elif ai_reply:
            reply_text = ai_reply(target, content)
        else:
            logger.info("[%s] pending: %s (no reply configured)", target, content)
            continue

        if not reply_text:
            continue

        send_message_smart(wx.chat_window, target, reply_text, target_type)
        record_outgoing_fn(state, target, reply_text)
        state[last_replied_key_fn(target)] = key
        if msg_type in ("image", "document") and ai_reply:
            try:
                from wx4py_mcp.conversation_memory import append_exchange, is_memory_enabled

                if is_memory_enabled():
                    label = "图片" if msg_type == "image" else "文件"
                    append_exchange(
                        target,
                        target_type,
                        f"[发送了{label}]",
                        reply_text[:800],
                    )
            except Exception as exc:
                logger.debug("[memory] media exchange skip: %s", exc)
        tag = "startup" if phase == "startup" else target
        logger.info("[%s] replied once to: %s", tag, content[:60])
        logger.info("[%s] reply: %s", tag, reply_text[:80])
        handled += 1
        if should_exit:
            break

    return handled, should_exit


def run_startup_catchup(
    wx,
    targets: list[str],
    target_type: str,
    state: dict[str, Any],
    msg_filter,
    fixed_reply: str,
    ai_reply: Optional[Callable[[str, str], str]],
    echo_reply: bool,
    **kwargs,
) -> tuple[int, bool]:
    """On listener start: detect last peer line, recognize, reply, then enter poll loop."""
    logger.info("[startup] catch-up for %s", ", ".join(targets))
    return process_targets_once(
        wx,
        targets,
        target_type,
        state,
        msg_filter,
        fixed_reply,
        ai_reply,
        echo_reply,
        phase="startup",
        **kwargs,
    )
