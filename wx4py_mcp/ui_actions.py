"""Shared low-level UI click helpers."""

from __future__ import annotations

import time

import win32api
import win32con


def click_control(control) -> bool:
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


def click_rect_center(rect, x_ratio: float = 0.35) -> None:
    x = int(rect.left + max(20, (rect.right - rect.left) * x_ratio))
    y = (rect.top + rect.bottom) // 2
    win32api.SetCursorPos((x, y))
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
    time.sleep(0.05)
    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)


def double_click_rect_center(rect, x_ratio: float = 0.5) -> None:
    """Double-click bubble/preview center — WeChat opens or zooms image."""
    x = int(rect.left + max(20, (rect.right - rect.left) * x_ratio))
    y = (rect.top + rect.bottom) // 2
    win32api.SetCursorPos((x, y))
    for _ in range(2):
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        time.sleep(0.08)


def double_click_control(control) -> bool:
    try:
        rect = control.BoundingRectangle
        double_click_rect_center(rect)
        return True
    except Exception:
        return click_control(control)


def press_escape() -> None:
    try:
        win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, 0)
        time.sleep(0.02)
        win32api.keybd_event(win32con.VK_ESCAPE, 0, 0, win32con.KEYEVENTF_KEYUP)
    except Exception:
        pass
