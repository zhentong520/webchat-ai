"""Read the last visible chat line with sender side (left grey=peer, right green=self)."""

from __future__ import annotations

import logging
import re
import time
from typing import Any, Optional

from PIL import ImageGrab

from wx4py_mcp.document_message import (
    document_runtime_id,
    is_document_message,
    resolve_document_content,
)
from wx4py_mcp.image_message import (
    is_image_message,
    image_runtime_id,
    resolve_image_content,
)
from wx4py_mcp.open_chat import has_chat_panel_open, is_chat_already_open, is_chat_open_for, open_chat_smart
from wx4py_mcp.voice_message import (
    is_voice_class,
    parse_voice_transcript,
    resolve_voice_content,
    voice_runtime_id,
)
from wx4py_mcp.wechat_lock import wechat_ui_lock

logger = logging.getLogger(__name__)

TIME_CLS = "mmui::ChatItemView"
MSG_TYPES = {"mmui::ChatTextItemView", "mmui::ChatBubbleItemView"}
TIME_RE = re.compile(
    r"^(今天|昨天|星期[一二三四五六日]|\d{1,2}月\d{1,2}日|\d{1,2}/\d{1,2}|\d{4}年|\d{1,2}:\d{2})"
)


def _green_score(pixel: tuple[int, ...]) -> int:
    red, green, blue = pixel[0], pixel[1], pixel[2]
    return green - max(red, blue)


def _detect_from_peer(list_rect, row_rect) -> bool:
    """Return True if the row looks like a left grey peer bubble (not right green self)."""
    list_w = max(int(list_rect.right - list_rect.left), 1)
    row_cx = (row_rect.left + row_rect.right) / 2
    list_cx = (list_rect.left + list_rect.right) / 2
    offset = row_cx - list_cx

    if offset > list_w * 0.14:
        return False
    if offset < -list_w * 0.14:
        return True

    try:
        img = ImageGrab.grab(
            (
                int(list_rect.left),
                int(row_rect.top),
                int(list_rect.right),
                int(row_rect.bottom),
            )
        )
    except Exception as exc:
        logger.warning("row screenshot failed: %s", exc)
        return False

    width, height = img.size
    if width < 20 or height < 5:
        return False

    right_greens = []
    left_greens = []
    for ratio in (0.35, 0.5, 0.65):
        y = max(2, min(height - 3, int(height * ratio)))
        left_px = img.getpixel((max(5, int(width * 0.18)), y))
        right_px = img.getpixel((min(width - 5, int(width * 0.82)), y))
        left_greens.append(_green_score(left_px))
        right_greens.append(_green_score(right_px))

    right_green = max(right_greens)
    left_green = max(left_greens)

    if right_green >= 42 and right_green > left_green + 18:
        return False
    if right_green < 30 and left_green < 30:
        return True
    return right_green <= left_green


def _read_last_visible_message(msg_list, convert_voice: bool = True, convert_image: bool = True, convert_document: bool = True) -> Optional[dict[str, Any]]:
    list_rect = msg_list.BoundingRectangle
    current_ts = ""
    last_item: Optional[dict[str, Any]] = None
    last_voice_ctrl = None
    last_image_ctrl = None
    last_document_ctrl = None

    try:
        children = msg_list.GetChildren()
    except Exception:
        return None

    for child in children:
        cls = child.ClassName or ""
        name = (child.Name or "").strip()
        if cls == TIME_CLS:
            if TIME_RE.match(name):
                current_ts = name
            continue

        if is_voice_class(cls):
            row_rect = child.BoundingRectangle
            last_voice_ctrl = child
            last_item = {
                "type": "voice",
                "content": parse_voice_transcript(name) or "",
                "time": current_ts,
                "from_peer": _detect_from_peer(list_rect, row_rect),
                "voice_id": voice_runtime_id(child),
                "raw_name": name,
            }
            continue

        if is_image_message(cls, name):
            row_rect = child.BoundingRectangle
            last_image_ctrl = child
            last_document_ctrl = None
            last_item = {
                "type": "image",
                "content": "",
                "time": current_ts,
                "from_peer": _detect_from_peer(list_rect, row_rect),
                "image_id": image_runtime_id(child),
                "raw_name": name,
            }
            continue

        if is_document_message(cls, name):
            row_rect = child.BoundingRectangle
            last_document_ctrl = child
            last_image_ctrl = None
            last_item = {
                "type": "document",
                "content": "",
                "time": current_ts,
                "from_peer": _detect_from_peer(list_rect, row_rect),
                "document_id": document_runtime_id(child),
                "raw_name": name,
            }
            continue

        if cls not in MSG_TYPES or not name:
            continue
        row_rect = child.BoundingRectangle
        last_voice_ctrl = None
        last_image_ctrl = None
        last_document_ctrl = None
        last_item = {
            "type": "text" if "Text" in cls else "link",
            "content": name,
            "time": current_ts,
            "from_peer": _detect_from_peer(list_rect, row_rect),
        }

    if not last_item:
        return None

    if last_item.get("type") == "voice" and convert_voice and not last_item.get("content") and last_voice_ctrl:
        last_item["content"] = resolve_voice_content(last_voice_ctrl) or ""

    if last_item.get("type") == "image" and convert_image and last_image_ctrl:
        last_item["content"] = resolve_image_content(
            last_image_ctrl, last_item.get("image_id") or ""
        ) or ""

    if last_item.get("type") == "document" and convert_document and last_document_ctrl:
        last_item["content"] = resolve_document_content(
            last_document_ctrl, last_item.get("raw_name") or ""
        ) or ""

    return last_item


def get_last_chat_line(chat_window, target: str, target_type: str = "contact") -> Optional[dict[str, Any]]:
    """
    Open chat (session list first), scroll to bottom once, return last visible line.
    """
    with wechat_ui_lock():
        if is_chat_already_open(chat_window, target):
            logger.info("[session] read: reusing open chat %s", target)
        elif has_chat_panel_open(chat_window) and is_chat_open_for(chat_window, target):
            logger.info("[session] read: chat panel already on %s (list row)", target)
        elif not open_chat_smart(chat_window, target, target_type):
            logger.error("cannot open chat: %s", target)
            return None

        time.sleep(0.4)
        msg_list = chat_window._get_chat_message_list()
        if not msg_list:
            return None

        cx, cy = chat_window._get_message_list_center(msg_list)
        msg_list.SetFocus()
        time.sleep(0.2)
        chat_window._scroll_message_list_to_bottom(msg_list, cx, cy)
        return _read_last_visible_message(msg_list)
