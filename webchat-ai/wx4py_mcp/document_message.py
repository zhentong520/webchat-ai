"""WeChat file/document message detection and text extraction."""

from __future__ import annotations

import logging
import os
import re
import time
from pathlib import Path
from typing import Any, Optional

from wx4py_mcp.media_reply import build_direct_media_reply
from wx4py_mcp.ui_actions import click_rect_center
from wx4py_mcp.vision_client import organize_document_text

logger = logging.getLogger(__name__)

FILE_REFER_CLASS = "mmui::ChatBubbleReferItemView"
FILE_CLASSES = frozenset(
    {
        "mmui::ChatFileItemView",
        "mmui::ChatFileBubbleView",
        FILE_REFER_CLASS,
    }
)
IMAGE_LABEL = "图片"
FILE_EXT_RE = re.compile(
    r"\.(pdf|docx?|xlsx?|pptx?|txt|md|csv|json|log|html?|rtf|epub)$",
    re.IGNORECASE,
)
TEXT_EXT = frozenset({".txt", ".md", ".csv", ".json", ".log", ".xml", ".html", ".htm"})
OPEN_FILE_WAIT = 2.5


def _looks_like_filename(name: str) -> bool:
    label = (name or "").strip()
    if not label or label == IMAGE_LABEL:
        return False
    if FILE_EXT_RE.search(label):
        return True
    if re.search(r"\(\d+(?:\.\d+)?[KMG]?\)", label, re.I):
        return True
    return False


def is_document_message(class_name: str, name: str) -> bool:
    cls = class_name or ""
    label = (name or "").strip()
    if cls in ("mmui::ChatFileItemView", "mmui::ChatFileBubbleView"):
        return True
    if cls == FILE_REFER_CLASS and _looks_like_filename(label):
        return True
    return False


def document_runtime_id(control) -> str:
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
        return "file:unknown"


def _wechat_file_roots() -> list[Path]:
    roots: list[Path] = []
    docs = Path.home() / "Documents"
    for pattern in ("WeChat Files", "xwechat_files", "WeChat"):
        p = docs / pattern
        if p.exists():
            roots.append(p)
    download = Path.home() / "Downloads"
    if download.exists():
        roots.append(download)
    custom = os.getenv("WX4PY_WECHAT_FILES_DIR", "").strip()
    if custom:
        cp = Path(custom)
        if cp.exists():
            roots.append(cp)
    return roots


def _find_downloaded_file(filename: str, since_ts: float) -> Optional[Path]:
    target_name = Path(filename).name
    if not target_name:
        return None
    candidates: list[Path] = []
    for root in _wechat_file_roots():
        try:
            for path in root.rglob(target_name):
                if path.is_file() and path.stat().st_mtime >= since_ts - 5:
                    candidates.append(path)
        except Exception:
            continue
    if not candidates:
        return None
    candidates.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return candidates[0]


def _read_text_file(path: Path) -> str:
    for enc in ("utf-8", "utf-8-sig", "gbk", "gb18030"):
        try:
            return path.read_text(encoding=enc)
        except Exception:
            continue
    return path.read_text(encoding="utf-8", errors="replace")


def _parse_file_to_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in TEXT_EXT:
        return _read_text_file(path)
    try:
        from markitdown import MarkItDown

        result = MarkItDown().convert(str(path))
        text = (result.text_content or "").strip()
        if text:
            return text
    except Exception as exc:
        logger.debug("[document] markitdown unavailable or failed: %s", exc)
    if ext == ".pdf":
        try:
            from pypdf import PdfReader

            reader = PdfReader(str(path))
            parts = []
            for page in reader.pages[:20]:
                parts.append(page.extract_text() or "")
            text = "\n".join(parts).strip()
            if text:
                return text
        except Exception as exc:
            logger.debug("[document] pypdf failed: %s", exc)
    return f"（已收到文件 {path.name}，当前环境暂无法完整解析该格式，请尝试发送 txt/pdf 或截图）"


def _trigger_file_open(file_control) -> None:
    """Click file bubble to trigger WeChat download — do not Esc (would close chat)."""
    click_rect_center(file_control.BoundingRectangle, x_ratio=0.5)
    time.sleep(OPEN_FILE_WAIT)


def resolve_document_content(file_control, filename_hint: str = "") -> Optional[str]:
    """Open/download file if needed, extract text, return direct reply body."""
    name = (filename_hint or "").strip()
    if not name and file_control:
        try:
            name = (file_control.Name or "").strip()
        except Exception:
            name = ""
    logger.info("[document] resolve file: %s", name[:80] or "(unknown)")
    since = time.time()
    _trigger_file_open(file_control)
    local_path = _find_downloaded_file(name, since) if name else None
    if not local_path:
        logger.warning("[document] file not found locally: %s", name)
        if name:
            return build_direct_media_reply(
                "document",
                f"已收到文件：{name}\n（未能自动下载到本地，请重新发送或改发图片/txt）",
            )
        return None
    logger.info("[document] found %s", local_path)
    try:
        raw = _parse_file_to_text(local_path)
        organized = organize_document_text(raw)
        return build_direct_media_reply("document", organized)
    except Exception as exc:
        logger.error("[document] parse failed: %s", exc)
        return build_direct_media_reply("document", f"文件 {local_path.name} 解析失败：{exc}")


def document_message_key(msg: dict[str, Any]) -> str:
    doc_id = msg.get("document_id") or ""
    content = (msg.get("content") or "").strip()
    name = (msg.get("raw_name") or "").strip()
    if content:
        return f"document:{doc_id}|{name}|{content[:120]}"
    return f"document:{doc_id}|{name}|pending"
