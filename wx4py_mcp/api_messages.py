"""Message MCP tools."""

from __future__ import annotations

from typing import Optional

from .client import get_client
from .call_control import start_video_call, start_voice_call
from .open_chat import send_message_smart
from .rpc import tool
from .utils import format_result


@tool(
    name="wechat_send",
    description="Send text message. Args: target, message, target_type (contact|group, default contact)",
)
def wechat_send(target: str, message: str, target_type: str = "contact") -> str:
    if not target or not message:
        return format_result(False, "target and message are required")
    try:
        wx = get_client()
        ok = send_message_smart(wx.chat_window, target, message, target_type)
        if not ok:
            return format_result(False, "send failed", {"target": target})
        return format_result(True, "sent", {"target": target, "target_type": target_type})
    except Exception as exc:
        return format_result(False, str(exc))


@tool(
    name="wechat_voice_call",
    description="Start voice call with contact. Opens chat, clicks call icon, selects 语音通话. Args: target, target_type",
)
def wechat_voice_call(target: str, target_type: str = "contact") -> str:
    if not target:
        return format_result(False, "target is required")
    try:
        wx = get_client()
        ok = start_voice_call(wx.chat_window, target, target_type)
        if not ok:
            return format_result(False, "voice call failed", {"target": target})
        return format_result(True, "voice call initiated", {"target": target, "call_type": "voice"})
    except Exception as exc:
        return format_result(False, str(exc))


@tool(
    name="wechat_video_call",
    description="Start video call with contact. Opens chat, clicks call icon, selects 视频通话. Args: target, target_type",
)
def wechat_video_call(target: str, target_type: str = "contact") -> str:
    if not target:
        return format_result(False, "target is required")
    try:
        wx = get_client()
        ok = start_video_call(wx.chat_window, target, target_type)
        if not ok:
            return format_result(False, "video call failed", {"target": target})
        return format_result(True, "video call initiated", {"target": target, "call_type": "video"})
    except Exception as exc:
        return format_result(False, str(exc))


@tool(
    name="wechat_get_history",
    description="Get chat history. Args: target, target_type (contact|group), since (today|yesterday|week|all)",
)
def wechat_get_history(
    target: str,
    target_type: str = "contact",
    since: str = "today",
    max_count: int = 50,
) -> str:
    try:
        wx = get_client()
        messages = wx.chat_window.get_chat_history(
            target=target,
            target_type=target_type,
            since=since,
            max_count=max_count,
        )
        return format_result(True, f"{len(messages)} messages", {"messages": messages})
    except Exception as exc:
        return format_result(False, str(exc))


@tool(
    name="wechat_send_file",
    description="Send file(s). Args: target, file_path (str or comma-separated paths), target_type, message (optional caption)",
)
def wechat_send_file(
    target: str,
    file_path: str,
    target_type: str = "contact",
    message: Optional[str] = None,
) -> str:
    try:
        wx = get_client()
        paths = [p.strip() for p in file_path.split(",") if p.strip()]
        payload = paths[0] if len(paths) == 1 else paths
        wx.chat_window.send_file_to(target, payload, target_type=target_type, message=message)
        return format_result(True, "file sent", {"target": target, "files": paths})
    except Exception as exc:
        return format_result(False, str(exc))
