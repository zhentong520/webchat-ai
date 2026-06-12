"""WeChat image message capture + vision understanding."""

from __future__ import annotations

import logging
import os
import time
import uuid
from pathlib import Path
from typing import Any, Optional

from PIL import Image, ImageFilter, ImageGrab, ImageOps

from wx4py_mcp.open_chat import _safe_text
from wx4py_mcp.ui_actions import (
    double_click_rect_center,
    press_escape,
)
from wx4py_mcp.media_reply import build_direct_media_reply
from wx4py_mcp.vision_client import analyze_image

logger = logging.getLogger(__name__)

IMAGE_REFER_CLASS = "mmui::ChatBubbleReferItemView"
IMAGE_LABEL = "图片"
IMAGE_CLASSES = frozenset(
    {
        IMAGE_REFER_CLASS,
        "mmui::ChatImageItemView",
        "mmui::ChatImageBubbleView",
    }
)
PREVIEW_WINDOW_CLASS = "mmui::PreviewWindow"
PREVIEW_IMAGE_CLASS = "mmui::PreviewImage"
PREVIEW_OPEN_TIMEOUT = 2.5
PREVIEW_OPEN_WAIT = float(os.getenv("WX4PY_IMAGE_PREVIEW_WAIT", "0.55"))
PREVIEW_ZOOM = os.getenv("WX4PY_IMAGE_PREVIEW_ZOOM", "0") == "1"
IMAGE_CACHE_DIR = Path(os.getenv("WX4PY_STATE_DIR", str(Path.home() / ".wx4py-mcp"))) / "images"

MIN_LONG_EDGE = int(os.getenv("WX4PY_IMAGE_MIN_EDGE", "300"))
MIN_SHORT_EDGE = int(os.getenv("WX4PY_IMAGE_MIN_SHORT", "140"))
BLUR_LAPLACIAN_THRESHOLD = float(os.getenv("WX4PY_IMAGE_BLUR_THRESHOLD", "35"))
THUMB_CAPTURE_MIN = int(os.getenv("WX4PY_IMAGE_THUMB_MIN", "48"))
SKIP_BLUR_CHECK = os.getenv("WX4PY_IMAGE_SKIP_BLUR_CHECK", "1") == "1"


def _preview_is_open() -> bool:
    return _find_preview_window() is not None


def _close_preview_if_open() -> None:
    """Close image preview only — never Esc when preview is absent (Esc would close chat)."""
    if not _preview_is_open():
        logger.info("[image] preview not open, skip Esc")
        return
    logger.info("[image] close preview window")
    press_escape()
    time.sleep(0.35)
    if _preview_is_open():
        logger.info("[image] preview still open, Esc once more")
        press_escape()
        time.sleep(0.25)


def is_image_message(class_name: str, name: str) -> bool:
    cls = class_name or ""
    label = (name or "").strip()
    if cls == IMAGE_REFER_CLASS and label == IMAGE_LABEL:
        return True
    if cls in IMAGE_CLASSES and label in (IMAGE_LABEL, "[图片]"):
        return True
    return False


def image_runtime_id(control) -> str:
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
        return "image:unknown"


def _laplacian_variance(img: Image.Image) -> float:
    gray = ImageOps.grayscale(img)
    lap = gray.filter(
        ImageFilter.Kernel((3, 3), (0, 1, 0, 1, -4, 1, 0, 1, 0), scale=1, offset=0)
    )
    pixels = list(lap.get_flattened_data())
    if not pixels:
        return 0.0
    mean = sum(pixels) / len(pixels)
    return sum((p - mean) ** 2 for p in pixels) / len(pixels)


def needs_preview_enlarge(path: Path) -> tuple[bool, str]:
    """Return True when thumbnail is too small or too blurry for OCR."""
    try:
        with Image.open(path) as img:
            w, h = img.size
            long_edge = max(w, h)
            short_edge = min(w, h)
            if long_edge < MIN_LONG_EDGE:
                return True, f"resolution {w}x{h}"
            if short_edge < MIN_SHORT_EDGE:
                return True, f"short edge {short_edge}px"
            if not SKIP_BLUR_CHECK:
                score = _laplacian_variance(img)
                if score < BLUR_LAPLACIAN_THRESHOLD:
                    return True, f"blur score {score:.1f}"
            return False, "sharp enough"
    except Exception as exc:
        logger.warning("[image] quality check failed: %s", exc)
        return True, "quality check failed"


def _find_preview_window():
    from wx4py.core import uiautomation as uia

    deadline = time.time() + PREVIEW_OPEN_TIMEOUT
    while time.time() < deadline:
        for window in uia.GetRootControl().GetChildren():
            if PREVIEW_WINDOW_CLASS in (_safe_text(window, "ClassName") or ""):
                return window
        time.sleep(0.08)
    return None


def _find_preview_image(preview_window):
    from wx4py.core import uiautomation as uia

    for control, _depth in uia.WalkControl(preview_window, includeTop=True, maxDepth=12):
        if _safe_text(control, "ClassName") == PREVIEW_IMAGE_CLASS:
            return control
    return None


def _save_rect_image(rect, dest: Path) -> bool:
    try:
        img = ImageGrab.grab((int(rect.left), int(rect.top), int(rect.right), int(rect.bottom)))
        if img.size[0] < 8 or img.size[1] < 8:
            return False
        img.save(dest, format="JPEG", quality=90, optimize=True)
        return dest.exists() and dest.stat().st_size > 0
    except Exception as exc:
        logger.warning("[image] screenshot failed: %s", exc)
        return False


def _save_control_image(control, dest: Path) -> bool:
    try:
        if control.CaptureToImage(str(dest)):
            if dest.exists() and dest.stat().st_size > 0:
                return True
    except Exception as exc:
        logger.debug("[image] CaptureToImage failed: %s", exc)
    try:
        return _save_rect_image(control.BoundingRectangle, dest)
    except Exception:
        return False


def _bubble_large_enough(control, min_size: int = THUMB_CAPTURE_MIN) -> bool:
    try:
        rect = control.BoundingRectangle
        w = int(rect.right - rect.left)
        h = int(rect.bottom - rect.top)
        return w >= min_size and h >= min_size
    except Exception:
        return False


def _capture_thumbnail(image_control, dest: Path) -> bool:
    if not _bubble_large_enough(image_control):
        return False
    logger.info("[image] capture thumbnail from chat bubble")
    return _save_rect_image(image_control.BoundingRectangle, dest)


def _capture_from_preview(image_control, dest: Path) -> bool:
    logger.info("[image] open preview for capture")
    double_click_rect_center(image_control.BoundingRectangle)
    time.sleep(PREVIEW_OPEN_WAIT)

    preview = _find_preview_window()
    if not preview:
        logger.warning("[image] preview window not found")
        return False

    if PREVIEW_ZOOM:
        from wx4py_mcp.ui_actions import double_click_control

        preview_image = _find_preview_image(preview)
        if preview_image:
            double_click_control(preview_image)
            time.sleep(0.3)

    preview_image = _find_preview_image(preview)
    target = preview_image or preview
    ok = _save_control_image(target, dest)
    if ok:
        logger.info("[image] saved preview %s (%sKB)", dest.name, dest.stat().st_size // 1024)
    _close_preview_if_open()
    return ok


def capture_image_file(image_control) -> Optional[Path]:
    """
    Capture chat image for vision OCR.

    1. Try bubble thumbnail (fast path).
    2. If blurry / too small → double-click to open preview, zoom, capture.
    3. Preview window stays open until resolve_image_content finishes parsing.
    """
    IMAGE_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    dest = IMAGE_CACHE_DIR / f"{uuid.uuid4().hex}.jpg"

    if _capture_thumbnail(image_control, dest):
        enlarge, reason = needs_preview_enlarge(dest)
        if not enlarge:
            logger.info("[image] thumbnail ok (%s)", reason)
            return dest
        logger.info("[image] thumbnail needs preview: %s", reason)
        try:
            dest.unlink(missing_ok=True)
        except Exception:
            pass
    else:
        logger.info("[image] bubble too small, open preview")

    preview_dest = IMAGE_CACHE_DIR / f"{uuid.uuid4().hex}.jpg"
    if _capture_from_preview(image_control, preview_dest):
        return preview_dest

    if _preview_is_open():
        _close_preview_if_open()
    return None


def resolve_image_content(image_control, image_id: str = "") -> Optional[str]:
    """Capture image, vision OCR, return text ready for direct reply."""
    path: Optional[Path] = None
    preview_was_open = False
    try:
        preview_was_open = _preview_is_open()
        path = capture_image_file(image_control)
        if not path:
            return None

        started = time.time()
        vision_text = analyze_image(path)
        logger.info("[image] total resolve in %.1fs", time.time() - started)
        return build_direct_media_reply("image", vision_text)
    except Exception as exc:
        logger.error("[image] vision failed: %s", exc)
        return None
    finally:
        if preview_was_open or _preview_is_open():
            _close_preview_if_open()
        if path:
            try:
                path.unlink(missing_ok=True)
            except Exception:
                pass


def image_message_key(msg: dict[str, Any]) -> str:
    image_id = msg.get("image_id") or ""
    content = (msg.get("content") or "").strip()
    if content:
        return f"image:{image_id}|{content}"
    return f"image:{image_id}|pending"
