"""WeChat voice message → text via native 语音转文字 context menu."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

import win32api
import win32con

from wx4py_mcp.open_chat import _safe_text

logger = logging.getLogger(__name__)

VOICE_CLASSES = frozenset(
    {
        "mmui::ChatVoiceItemView",
        "mmui::ChatVoiceBubbleView",
    }
)
VOICE_MENU_LABELS = ("语音转文字", "转文字", "转换为文字")
# After conversion WeChat appends transcript to Name, e.g. 语音4"秒你好，在吗
VOICE_NAME_RE = re.compile(r'^语音(\d+)"秒(?:未播放)?(.*)$', re.DOTALL)
VOICE_CONVERT_TIMEOUT = 18.0
VOICE_CONVERT_POLL = 0.4


def is_voice_class(class_name: str) -> bool:
    return (class_name or "") in VOICE_CLASSES


def voice_runtime_id(control) -> str:
    try:
        rid = control.GetRuntimeId()
        if rid:
            return "rid:" + "-".join(str(x) for x in rid)
    except Exception:
        pass
    try:
        rect = control.BoundingRectangle
        return f"rect:{rect.top},{rect.left},{rect.bottom},{rect.right}"
    except Exception:
        return "voice:unknown"


def parse_voice_transcript(name: str) -> Optional[str]:
    """Return transcript if WeChat already converted this voice bubble."""
    text = (name or "").strip()
    match = VOICE_NAME_RE.match(text)
    if not match:
        return None
    transcript = (match.group(2) or "").strip()
    return transcript or None


def _click_control(control) -> bool:
    try:
        control.Click(simulateMove=False)
        return True
    except Exception:
        pass
    try:
        rect = control.BoundingRectangle
        x = (rect.left + rect.right) // 2
        y = (rect.top + rect.bottom) // 2
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return True
    except Exception:
        return False


def _right_click_voice(control) -> None:
    rect = control.BoundingRectangle
    x = int(rect.left + max(40, (rect.right - rect.left) * 0.22))
    y = (rect.top + rect.bottom) // 2
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
    time.sleep(0.35)


def _find_voice_menu_item(label: str):
    from wx4py.core import uiautomation as uia

    for window in uia.GetRootControl().GetChildren():
        if _safe_text(window, "Name") != "微信":
            continue
        for control, _depth in uia.WalkControl(window, includeTop=True, maxDepth=15):
            if _safe_text(control, "Name") != label:
                continue
            if _safe_text(control, "ControlTypeName") != "MenuItemControl":
                continue
            return control
    return None


def _dismiss_context_menu() -> None:
    try:
        win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
        time.sleep(0.02)
        win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, win32con.KEYEVENTF_KEYUP)
    except Exception:
        pass


def convert_voice_to_text(voice_control, timeout: float = VOICE_CONVERT_TIMEOUT) -> Optional[str]:
    """
    Right-click voice bubble → 语音转文字 → read transcript from control Name.
    """
    existing = parse_voice_transcript(_safe_text(voice_control, "Name"))
    if existing:
        logger.info("[voice] already converted: %s", existing[:60])
        return existing

    logger.info("[voice] convert via context menu: %r", _safe_text(voice_control, "Name")[:40])
    _right_click_voice(voice_control)

    menu_item = None
    for label in VOICE_MENU_LABELS:
        menu_item = _find_voice_menu_item(label)
        if menu_item:
            logger.info("[voice] click menu: %s", label)
            break

    if not menu_item:
        logger.warning("[voice] menu item not found")
        _dismiss_context_menu()
        return None

    if not _click_control(menu_item):
        logger.warning("[voice] failed to click menu item")
        _dismiss_context_menu()
        return None

    deadline = time.time() + timeout
    while time.time() < deadline:
        time.sleep(VOICE_CONVERT_POLL)
        transcript = parse_voice_transcript(_safe_text(voice_control, "Name"))
        if transcript:
            logger.info("[voice] transcript: %s", transcript[:80])
            return transcript

    logger.warning("[voice] conversion timed out")
    return None


def resolve_voice_content(voice_control) -> Optional[str]:
    """Return transcript, converting first when needed."""
    transcript = parse_voice_transcript(_safe_text(voice_control, "Name"))
    if transcript:
        return transcript
    return convert_voice_to_text(voice_control)


def voice_message_key(msg: dict[str, Any]) -> str:
    voice_id = msg.get("voice_id") or ""
    content = (msg.get("content") or "").strip()
    if content:
        return f"voice:{voice_id}|{content}"
    return f"voice:{voice_id}|pending"
