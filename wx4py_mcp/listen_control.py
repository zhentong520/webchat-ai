"""Pause/resume auto-reply via chat commands (polling keeps running)."""

from __future__ import annotations

STOP_PHRASES = (
    "停止监听",
    "停止自动回复",
    "别自动回复",
    "不要自动回复",
    "不要乱回答",
    "别乱回答",
)

START_PHRASES = (
    "开始监听",
    "恢复监听",
    "继续监听",
    "继续自动回复",
)

VIDEO_CALL_PHRASES = (
    "视频通话",
    "视频对话",
    "发起视频",
    "视频呼叫",
)

VOICE_CALL_PHRASES = (
    "语音通话",
    "发起语音",
    "语音呼叫",
)

PAUSED_SUFFIX = "__paused__"
WELCOME_MSG = (
    "你好！我是AI小宝，你可以跟我唠唠嗑。"
    "如果不想让我继续回复了，就发送「停止监听」。"
)
ACK_STOP = "好的，已停止监听，不再轮询。需要时重新运行启动脚本即可。"
ACK_START = "好的，已恢复自动回复。"
ACK_VIDEO_CALL = "好的，正在发起视频通话～"
ACK_VOICE_CALL = "好的，正在发起语音通话～"
ACK_CALL_FAIL = "抱歉，通话发起失败，请稍后再试。"


def paused_key(contact: str) -> str:
    return f"{contact}{PAUSED_SUFFIX}"


def is_paused(state: dict, contact: str) -> bool:
    return bool(state.get(paused_key(contact), False))


def set_paused(state: dict, contact: str, paused: bool) -> None:
    state[paused_key(contact)] = paused


def match_control_command(content: str) -> str | None:
    text = (content or "").strip()
    if not text:
        return None
    if any(phrase in text for phrase in STOP_PHRASES):
        return "stop"
    if any(phrase in text for phrase in START_PHRASES):
        return "start"
    return None


def match_call_command(content: str) -> str | None:
    """Return 'video' | 'voice' when peer asks to start a call."""
    text = (content or "").strip()
    if not text:
        return None
    if any(phrase in text for phrase in VIDEO_CALL_PHRASES):
        return "video"
    if any(phrase in text for phrase in VOICE_CALL_PHRASES):
        return "voice"
    return None
