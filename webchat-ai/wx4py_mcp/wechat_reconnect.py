"""Reconnect wx4py client after WeChat restart."""

from __future__ import annotations

import logging

import win32gui
from wx4py import WeChatClient

logger = logging.getLogger(__name__)


def ensure_wechat_connected(wx: WeChatClient) -> WeChatClient:
    """Reconnect when the bound HWND is gone (e.g. user restarted WeChat)."""
    hwnd = None
    try:
        if wx.is_connected:
            hwnd = wx.window.hwnd
    except Exception:
        hwnd = None

    if hwnd and win32gui.IsWindow(hwnd):
        return wx

    logger.warning("[wechat] window lost — reconnecting")
    try:
        wx.disconnect()
    except Exception:
        pass
    try:
        wx.connect()
    except Exception as exc:
        logger.error("[wechat] reconnect failed: %s", exc)
        raise
    return wx
