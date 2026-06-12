"""Open WeChat chat: prefer visible session-list click, fallback to search."""

from __future__ import annotations

import logging
import time

import win32api
import win32con

from wx4py_mcp.wechat_lock import wechat_ui_lock

logger = logging.getLogger(__name__)

SESSION_ITEM_PREFIX = "session_item_"
CHAT_INPUT_PLACEHOLDERS = frozenset(
    {"微信", "WeChat", "发消息", "输入消息", "Type a message", "Message"}
)
TITLE_BAR_CLASSES = (
    "mmui::ChatTitleBarChatSingleView",
    "mmui::ChatTitleBarView",
    "mmui::ChatTitleBarChatRoomView",
)


def _safe_text(control, attr: str) -> str:
    try:
        value = getattr(control, attr, "") or ""
        return str(value)
    except Exception:
        return ""


def session_display_name(name: str) -> str:
    """Left list row title — first line only (red-box name in screenshot)."""
    return (name or "").split("\n")[0].strip()


def chat_title_matches(active: str, target: str) -> bool:
    left = session_display_name(active)
    right = session_display_name(target)
    if not left or not right:
        return False
    if left == right:
        return True
    # Input placeholder may append hints, e.g. "coco 按住 Ctrl + Win 使用语音输入文字"
    if left.startswith(right + " ") or left.startswith(right + "\u3000"):
        return True
    return False


def _session_item_automation_id(target: str) -> str:
    return f"{SESSION_ITEM_PREFIX}{target}"


def _is_session_cell(control) -> bool:
    cls = _safe_text(control, "ClassName")
    aid = _safe_text(control, "AutomationId")
    if "ChatSessionCell" in cls:
        return True
    if aid.startswith(SESSION_ITEM_PREFIX):
        return True
    if "Session" in cls and "Cell" in cls:
        return True
    return False


def _focus_wechat_soft(chat_window) -> None:
    """Bring WeChat to front once. No tray restore unless the window is truly hidden."""
    try:
        from wx4py.core.win32 import bring_window_to_front, get_foreground_window, is_window_visible

        hwnd = chat_window._window.hwnd
        if not hwnd:
            return
        if is_window_visible(hwnd):
            if get_foreground_window() != hwnd:
                bring_window_to_front(hwnd)
                time.sleep(0.12)
            return
    except Exception:
        pass

    logger.info("[session] WeChat not visible, activate once")
    chat_window._window.activate()
    time.sleep(0.25)


def _find_session_list(root):
    try:
        session_list = root.ListControl(AutomationId="session_list")
        if session_list.Exists(maxSearchSeconds=0.4):
            return session_list
    except Exception:
        pass

    try:
        from wx4py.core import uiautomation as uia

        for control, _depth in uia.WalkControl(root, includeTop=True, maxDepth=10):
            if _safe_text(control, "ControlTypeName") != "ListControl":
                continue
            auto_id = _safe_text(control, "AutomationId")
            name = _safe_text(control, "Name")
            if auto_id == "session_list" or name == "会话":
                return control
    except Exception:
        return None
    return None


def _count_session_items(session_list) -> int:
    try:
        from wx4py.core import uiautomation as uia

        return sum(
            1
            for control, _depth in uia.WalkControl(session_list, includeTop=False, maxDepth=4)
            if _is_session_cell(control)
        )
    except Exception:
        return 0


def _wait_session_list_ready(root, timeout: float = 1.2):
    """Brief wait on the current UI — no restore, no Esc."""
    deadline = time.time() + timeout
    last_list = None
    while time.time() < deadline:
        last_list = _find_session_list(root)
        if last_list and _count_session_items(last_list) > 0:
            return last_list
        time.sleep(0.2)
    return last_list


def _title_from_title_bar(root) -> str:
    try:
        from wx4py.core import uiautomation as uia

        for control, _depth in uia.WalkControl(root, includeTop=True, maxDepth=14):
            cls = _safe_text(control, "ClassName")
            if cls not in TITLE_BAR_CLASSES:
                continue
            for child, _ in uia.WalkControl(control, includeTop=False, maxDepth=4):
                if _safe_text(child, "ControlTypeName") != "TextControl":
                    continue
                name = _safe_text(child, "Name").strip()
                if name and name not in ("微信", "WeChat"):
                    return session_display_name(name)
    except Exception:
        pass
    return ""


def _get_selected_session_name(chat_window) -> str:
    session_list = _find_session_list(chat_window.root)
    if not session_list:
        return ""
    try:
        from wx4py.core import uiautomation as uia

        for control, _depth in uia.WalkControl(session_list, includeTop=False, maxDepth=4):
            if not _is_session_cell(control):
                continue
            try:
                if control.IsSelected:
                    return session_display_name(_safe_text(control, "Name"))
            except Exception:
                continue
    except Exception:
        pass
    return ""


def get_active_chat_title(chat_window) -> str:
    """Current chat title from input placeholder, title bar, or selected session row."""
    chat_input = chat_window._get_chat_input()
    if chat_input:
        name = session_display_name(_safe_text(chat_input, "Name"))
        if name and name not in CHAT_INPUT_PLACEHOLDERS:
            return name

    title = _title_from_title_bar(chat_window.root)
    if title:
        return title

    selected = _get_selected_session_name(chat_window)
    if selected:
        return selected

    try:
        from wx4py.core import uiautomation as uia

        for control, _depth in uia.WalkControl(chat_window.root, includeTop=True, maxDepth=10):
            cls = _safe_text(control, "ClassName")
            if cls != "mmui::ChatMasterView":
                continue
            for child, _ in uia.WalkControl(control, includeTop=False, maxDepth=4):
                if _safe_text(child, "ControlTypeName") != "TextControl":
                    continue
                name = session_display_name(_safe_text(child, "Name"))
                if name and len(name) <= 64:
                    return name
    except Exception:
        pass
    return ""


def has_chat_panel_open(chat_window) -> bool:
    """True when the right-side chat panel is active (not search-only / login)."""
    try:
        if chat_window._get_chat_input():
            return True
        if chat_window._get_chat_message_list():
            return True
    except Exception:
        pass
    return False


def is_search_overlay_active(chat_window) -> bool:
    """True when the global Ctrl+F search popover is visible."""
    try:
        popup = chat_window._get_search_popup()
        if popup and popup.Exists(maxSearchSeconds=0.2):
            return True
    except Exception:
        pass
    return False


def _safe_dismiss_search(chat_window) -> None:
    """Send Esc only when search overlay is open — never close an active chat."""
    if not is_search_overlay_active(chat_window):
        logger.info("[session] skip Esc — no search overlay (keep chat open)")
        return
    logger.info("[session] dismiss search overlay")
    try:
        chat_window._clear_search()
    except Exception:
        pass
    time.sleep(0.15)


def is_chat_open_for(chat_window, target: str) -> bool:
    """True when the right panel is already showing the target conversation."""
    if not has_chat_panel_open(chat_window):
        return False
    active = get_active_chat_title(chat_window)
    if chat_title_matches(active, target):
        return True
    selected = _get_selected_session_name(chat_window)
    if chat_title_matches(selected, target):
        return True
    return False


def is_chat_already_open(chat_window, target: str) -> bool:
    return is_chat_open_for(chat_window, target)


def _match_target_in_list(session_list, target: str):
    auto_id = _session_item_automation_id(target)
    try:
        item = session_list.ListItemControl(AutomationId=auto_id)
        if item.Exists(maxSearchSeconds=0.2) and _is_session_cell(item):
            return item
    except Exception:
        pass

    try:
        from wx4py.core import uiautomation as uia

        for control, _depth in uia.WalkControl(session_list, includeTop=False, maxDepth=4):
            ctype = _safe_text(control, "ControlTypeName")
            if ctype not in ("ListItemControl", "CustomControl"):
                continue
            if not _is_session_cell(control):
                continue
            if session_display_name(_safe_text(control, "Name")) != target:
                continue
            return control
    except Exception:
        return None
    return None


def _scroll_session_list(session_list, delta: int = -120, steps: int = 2) -> None:
    try:
        rect = session_list.BoundingRectangle
        x = (rect.left + rect.right) // 2
        y = (rect.top + rect.bottom) // 2
        session_list.SetFocus()
        win32api.SetCursorPos((x, y))
        for _ in range(steps):
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
            time.sleep(0.06)
    except Exception:
        pass
    time.sleep(0.2)


def find_session_item(
    chat_window,
    target: str,
    max_scroll_passes: int = 4,
    list_wait_timeout: float = 1.2,
):
    """
    Scan the visible session list on the current WeChat window.
    Scroll only — never restore tray or send Esc.
    """
    session_list = _find_session_list(chat_window.root)
    if not session_list or _count_session_items(session_list) == 0:
        session_list = _wait_session_list_ready(chat_window.root, timeout=list_wait_timeout)
    if not session_list:
        logger.info("[session] no session list on current UI for %r", target)
        return None

    for scroll_pass in range(max_scroll_passes + 1):
        item = _match_target_in_list(session_list, target)
        if item:
            logger.info(
                "[session] matched in list: %r id=%s scroll_pass=%s",
                target,
                _safe_text(item, "AutomationId"),
                scroll_pass,
            )
            return item
        if scroll_pass < max_scroll_passes:
            logger.info("[session] scrolling list (%s/%s) for %r", scroll_pass + 1, max_scroll_passes, target)
            _scroll_session_list(session_list)
            session_list = _find_session_list(chat_window.root) or session_list

    names = []
    try:
        from wx4py.core import uiautomation as uia

        for control, _depth in uia.WalkControl(session_list, includeTop=False, maxDepth=4):
            if _is_session_cell(control):
                names.append(session_display_name(_safe_text(control, "Name")))
    except Exception:
        pass
    logger.info("[session] %r not in visible list; rows=%s names=%s", target, len(names), names[:12])
    return None


def _click_session_name_area(control) -> bool:
    """Click the display-name area (left side of row, where user marks the red box)."""
    try:
        rect = control.BoundingRectangle
        x = rect.left + max(40, int((rect.right - rect.left) * 0.28))
        y = (rect.top + rect.bottom) // 2
        logger.info("[session] click list row for %r at (%s,%s)", _safe_text(control, "Name")[:20], x, y)
        win32api.SetCursorPos((x, y))
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
        time.sleep(0.05)
        win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
        return True
    except Exception as exc:
        logger.warning("[session] coordinate click failed: %s", exc)

    try:
        control.Click(simulateMove=False)
        return True
    except Exception:
        return False


def _wait_chat_open(chat_window, target: str, timeout: float = 2.0) -> bool:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if is_chat_open_for(chat_window, target):
            return True
        time.sleep(0.2)
    return False


def _click_search_result(target_result) -> bool:
    for method in (
        lambda: target_result.ctrl.Click(),
        lambda: target_result.ctrl.Click(simulateMove=False),
        lambda: target_result.ctrl.DoubleClick(simulateMove=False),
    ):
        try:
            method()
            return True
        except Exception:
            continue
    return False


def _open_via_search_once(chat_window, target: str, target_type: str) -> bool:
    """Single Ctrl+F search — safe Esc only when search overlay is open."""
    if is_chat_open_for(chat_window, target):
        logger.info("[session] already in target before search: %s", target)
        return True

    logger.info("[session] open via search (once): %s", target)
    try:
        results = chat_window.search(target)
    except Exception as exc:
        logger.error("[session] search failed: %s", exc)
        _safe_dismiss_search(chat_window)
        return False

    target_result = chat_window._find_target_result(results, target, target_type)
    if not target_result:
        logger.error("[session] search target not found: %s", target)
        _safe_dismiss_search(chat_window)
        return False

    if not _click_search_result(target_result):
        logger.error("[session] search result click failed: %s", target)
        _safe_dismiss_search(chat_window)
        return False

    time.sleep(0.5)
    if _wait_chat_open(chat_window, target, timeout=2.5):
        _safe_dismiss_search(chat_window)
        logger.info("[session] opened %s via search", target)
        return True

    if is_chat_open_for(chat_window, target):
        _safe_dismiss_search(chat_window)
        return True

    logger.warning("[session] search click did not confirm chat for %s", target)
    _safe_dismiss_search(chat_window)
    return False


def open_chat_smart(chat_window, target: str, target_type: str = "contact") -> bool:
    """
    On the current WeChat window (no repeated restore / close):
      1. If the open chat is already the target → done
      2. If chat panel is open → scan session list (longer wait after restart)
      3. Only if list miss → one Ctrl+F search (Esc never closes chat panel)
    """
    with wechat_ui_lock():
        _focus_wechat_soft(chat_window)

        active = get_active_chat_title(chat_window)
        if is_chat_open_for(chat_window, target):
            logger.info("[session] already in target chat: %s (active=%r)", target, active)
            return True

        panel_open = has_chat_panel_open(chat_window)
        list_timeout = 3.0 if panel_open else 2.0
        logger.info(
            "[session] current=%r need=%r panel_open=%s — scan list first",
            active or "(unknown)",
            target,
            panel_open,
        )

        item = find_session_item(chat_window, target, list_wait_timeout=list_timeout)
        if item:
            try:
                if item.IsSelected and is_chat_open_for(chat_window, target):
                    logger.info("[session] %s already selected in list", target)
                    return True
            except Exception:
                pass

            if _click_session_name_area(item) and _wait_chat_open(chat_window, target):
                logger.info("[session] switched to %s via list click", target)
                return True
            if is_chat_open_for(chat_window, target):
                logger.info("[session] %s open after list click (delayed title)", target)
                return True
            logger.warning("[session] list click did not switch to %s", target)
        else:
            logger.info("[session] %s not in visible list", target)

        if is_chat_open_for(chat_window, target):
            return True

        if panel_open:
            logger.info("[session] chat panel stays open — search once as fallback for %s", target)
        return _open_via_search_once(chat_window, target, target_type)


def send_message_smart(chat_window, target: str, message: str, target_type: str = "contact") -> bool:
    """Send message — reuse open chat panel; only reopen when panel is gone."""
    with wechat_ui_lock():
        _focus_wechat_soft(chat_window)
        if is_chat_open_for(chat_window, target) and has_chat_panel_open(chat_window):
            logger.info("[session] send: reusing open chat %s", target)
        elif not open_chat_smart(chat_window, target, target_type):
            logger.error("[session] cannot open chat for send: %s", target)
            return False
        ok = chat_window.send_message(message)
        logger.info("[session] send to %s: %s", target, "ok" if ok else "failed")
        return ok
