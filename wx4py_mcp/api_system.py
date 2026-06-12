"""System / status MCP tools."""

from __future__ import annotations

import wx4py

from .client import get_client
from .rpc import tool
from .utils import format_result


@tool(name="wechat_status", description="Check wx4py WeChat connection status")
def wechat_status() -> str:
    try:
        wx = get_client()
        return format_result(True, "connected", {"wx4py_version": getattr(wx4py, "__version__", "")})
    except Exception as exc:
        return format_result(False, str(exc))


@tool(name="wechat_list_tools", description="List wx4py-mcp tools")
def wechat_list_tools() -> str:
    lines = [
        "wechat_status - connection status",
        "wechat_send - send text to contact or group",
        "wechat_voice_call - start voice call (语音通话)",
        "wechat_video_call - start video call (视频通话)",
        "wechat_get_history - read chat history",
        "wechat_send_file - send file to contact or group",
    ]
    return "\n".join(lines)
