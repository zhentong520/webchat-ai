"""Initiate WeChat voice / video calls from the chat title bar."""

from __future__ import annotations

import logging
import time
from typing import Literal

import win32api
import win32con

from wx4py_mcp.open_chat import _safe_text, is_chat_open_for, open_chat_smart
from wx4py_mcp.wechat_lock import wechat_ui_lock

logger = logging.getLogger(__name__)

CallType = Literal["voice", "video"]
VOICE_LABEL = "语音通话"
VIDEO_LABEL = "视频通话"
VOIP_BUTTON_ID = "voip_button"


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


def _find_voip_trigger(chat_window):
    """Title-bar phone icon that opens the call menu (see user screenshot red box)."""
    root = chat_window.root
    try:
        btn = root.ButtonControl(AutomationId=VOIP_BUTTON_ID)
        if btn.Exists(maxSearchSeconds=0.5):
            return btn
    except Exception:
        pass

    try:
        from wx4py.core import uiautomation as uia

        for control, _depth in uia.WalkControl(root, includeTop=True, maxDepth=20):
            cls = _safe_text(control, "ClassName")
            if cls != "mmui::ChatVoIPView":
                continue
            for child, _ in uia.WalkControl(control, includeTop=False, maxDepth=3):
                if _safe_text(child, "ControlTypeName") != "ButtonControl":
                    continue
                return child
    except Exception:
        pass
    return None


def _find_call_menu_item(chat_window, label: str):
    """Find dropdown menu row: 语音通话 / 视频通话."""
    root = chat_window.root
    try:
        from wx4py.core import uiautomation as uia

        trigger = _find_voip_trigger(chat_window)
        trigger_bottom = trigger.BoundingRectangle.bottom if trigger else 0
        candidates = []
        for control, _depth in uia.WalkControl(root, includeTop=True, maxDepth=22):
            if _safe_text(control, "Name") != label:
                continue
            ctype = _safe_text(control, "ControlTypeName")
            if ctype not in ("ButtonControl", "ListItemControl", "MenuItemControl"):
                continue
            if _safe_text(control, "AutomationId") == VOIP_BUTTON_ID and label == VOICE_LABEL:
                continue
            rect = control.BoundingRectangle
            if rect.bottom <= trigger_bottom + 2:
                continue
            candidates.append((rect.top, control))
        if not candidates:
            return None
        candidates.sort(key=lambda item: item[0])
        return candidates[0][1]
    except Exception:
        return None


def _open_call_menu(chat_window) -> bool:
    trigger = _find_voip_trigger(chat_window)
    if not trigger:
        logger.error("[call] voip trigger button not found")
        return False
    logger.info("[call] click title-bar call icon (voip_button)")
    if not _click_control(trigger):
        return False
    time.sleep(0.45)
    return True


def start_call(
    chat_window,
    target: str,
    call_type: CallType = "voice",
    target_type: str = "contact",
) -> bool:
    """
    Open target chat, click title-bar call icon, choose voice or video from menu.

    UI path (from screenshot):
      chat header right → phone/camera icon → 语音通话 / 视频通话
    """
    label = VOICE_LABEL if call_type == "voice" else VIDEO_LABEL
    with wechat_ui_lock():
        if not open_chat_smart(chat_window, target, target_type):
            logger.error("[call] cannot open chat: %s", target)
            return False
        if not is_chat_open_for(chat_window, target):
            logger.error("[call] chat not ready for %s", target)
            return False

        if not _open_call_menu(chat_window):
            return False

        item = _find_call_menu_item(chat_window, label)
        if not item:
            logger.error("[call] menu item not found: %s", label)
            return False

        logger.info("[call] click menu: %s -> %s", target, label)
        if not _click_control(item):
            logger.error("[call] click failed: %s", label)
            return False
        time.sleep(0.3)
        return True


def start_voice_call(chat_window, target: str, target_type: str = "contact") -> bool:
    return start_call(chat_window, target, "voice", target_type)


def start_video_call(chat_window, target: str, target_type: str = "contact") -> bool:
    return start_call(chat_window, target, "video", target_type)
