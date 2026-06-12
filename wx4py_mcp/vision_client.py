"""Vision model client for WeChat image understanding."""

from __future__ import annotations

import base64
import hashlib
import io
import json
import logging
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from PIL import Image

from wx4py_mcp.ai_config import load_ai_config
from wx4py_mcp.workbuddy_model import (
    DEFAULT_BASE,
    ResolvedModel,
    _from_mmx,
    _from_openclaw,
    _from_workbuddy_models,
    _normalize_base,
    clean_reply_text,
)

logger = logging.getLogger(__name__)

VISION_MODEL_DEFAULT = "MiniMax-M3"
VISION_MAX_EDGE = int(os.getenv("WX4PY_VISION_MAX_EDGE", "1280"))
VISION_JPEG_QUALITY = int(os.getenv("WX4PY_VISION_JPEG_QUALITY", "82"))
VISION_API_TIMEOUT = float(os.getenv("WX4PY_VISION_TIMEOUT", "45"))
VISION_CACHE_ENABLED = os.getenv("WX4PY_VISION_CACHE", "1") != "0"
VISION_CACHE_DIR = Path(os.getenv("WX4PY_STATE_DIR", str(Path.home() / ".wx4py-mcp"))) / "vision_cache"

VISION_PROMPT = (
    "提取图中全部可见文字并按段落整理；无文字写「（无文字）」。"
    "最后一行以「——」开头写20字内概要。纯文本，不要 markdown。"
)

DOCUMENT_TEXT_PROMPT = (
    "以下是用户发来的文档提取文本。请整理成可直接发回给对方的纯文本：\n"
    "1) 保留关键信息与段落结构，删去乱码和重复空行；\n"
    "2) 最后一行以「——」开头写一句20字以内的内容概要。\n"
    "要求：不要 markdown、不要助手口吻。"
)


@dataclass
class VisionConfig:
    base_url: str
    model: str
    api_key: str
    source: str = ""


_config_cache: Optional[VisionConfig] = None


def _vision_from_ai_config() -> VisionConfig | None:
    path_block = None
    cfg_file = Path(os.getenv("WEBCHAT_AI_CONFIG", "")) if os.getenv("WEBCHAT_AI_CONFIG") else None
    from wx4py_mcp.ai_config import AI_CONFIG_FILE, _read_json

    data = _read_json(cfg_file or AI_CONFIG_FILE)
    if not isinstance(data, dict):
        return None
    block = data.get("vision")
    if not isinstance(block, dict):
        return None
    api_key = (block.get("api_key") or block.get("apiKey") or "").strip()
    if not api_key:
        return None
    return VisionConfig(
        base_url=_normalize_base(block.get("base_url") or block.get("baseUrl") or DEFAULT_BASE),
        model=(block.get("model") or VISION_MODEL_DEFAULT).strip(),
        api_key=api_key,
        source="config/ai-config.json#vision",
    )


def resolve_vision_model() -> VisionConfig:
    global _config_cache
    if _config_cache is not None:
        return _config_cache

    if os.getenv("WX4PY_VISION_API_KEY"):
        _config_cache = VisionConfig(
            base_url=_normalize_base(os.getenv("WX4PY_VISION_BASE_URL", DEFAULT_BASE)),
            model=os.getenv("WX4PY_VISION_MODEL", VISION_MODEL_DEFAULT),
            api_key=os.getenv("WX4PY_VISION_API_KEY", ""),
            source="env",
        )
        return _config_cache

    vision = _vision_from_ai_config()
    if vision:
        _config_cache = vision
        return _config_cache

    for name, fn in (
        ("mmx", _from_mmx),
        ("openclaw", _from_openclaw),
        ("workbuddy", _from_workbuddy_models),
    ):
        item: ResolvedModel | None = fn()
        if not item or not item.api_key:
            continue
        _config_cache = VisionConfig(
            base_url=_normalize_base(item.base_url),
            model=VISION_MODEL_DEFAULT,
            api_key=item.api_key,
            source=f"{name}/{VISION_MODEL_DEFAULT}",
        )
        return _config_cache

    text_cfg = load_ai_config()
    if text_cfg and text_cfg.api_key:
        _config_cache = VisionConfig(
            base_url=text_cfg.base_url,
            model=VISION_MODEL_DEFAULT,
            api_key=text_cfg.api_key,
            source=f"{text_cfg.source}→{VISION_MODEL_DEFAULT}",
        )
        return _config_cache

    raise RuntimeError(
        "未找到可用视觉模型配置。请在 ai-config.json 添加 vision 段，或配置本机 MiniMax API。"
    )


def prepare_image_for_api(path: Path) -> tuple[str, str]:
    """Resize + JPEG compress; return (data_url, content_sha256)."""
    with Image.open(path) as img:
        img = img.convert("RGB")
        width, height = img.size
        long_edge = max(width, height)
        if long_edge > VISION_MAX_EDGE:
            scale = VISION_MAX_EDGE / long_edge
            img = img.resize(
                (max(1, int(width * scale)), max(1, int(height * scale))),
                Image.Resampling.LANCZOS,
            )
        buf = io.BytesIO()
        img.save(buf, format="JPEG", quality=VISION_JPEG_QUALITY, optimize=True)
        raw = buf.getvalue()
    digest = hashlib.sha256(raw).hexdigest()
    data_url = f"data:image/jpeg;base64,{base64.b64encode(raw).decode('ascii')}"
    logger.info(
        "[image] prepared for API: %sKB sha=%s…",
        len(raw) // 1024,
        digest[:10],
    )
    return data_url, digest


def _cache_path(digest: str) -> Path:
    return VISION_CACHE_DIR / f"{digest}.json"


def get_cached_vision(digest: str) -> Optional[str]:
    if not VISION_CACHE_ENABLED or not digest:
        return None
    path = _cache_path(digest)
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        text = (data.get("text") or "").strip()
        if text:
            logger.info("[image] vision cache hit %s…", digest[:10])
            return text
    except Exception:
        pass
    return None


def set_cached_vision(digest: str, text: str) -> None:
    if not VISION_CACHE_ENABLED or not digest or not text:
        return
    VISION_CACHE_DIR.mkdir(parents=True, exist_ok=True)
    _cache_path(digest).write_text(
        json.dumps({"text": text, "ts": time.time()}, ensure_ascii=False),
        encoding="utf-8",
    )


def analyze_image(image_path: Path, prompt: str = VISION_PROMPT) -> str:
    """Return OCR + content summary for a local image file."""
    data_url, digest = prepare_image_for_api(image_path)
    cached = get_cached_vision(digest)
    if cached:
        return cached

    cfg = resolve_vision_model()
    url = f"{cfg.base_url.rstrip('/')}/chat/completions"
    payload = {
        "model": cfg.model,
        "messages": [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {"type": "image_url", "image_url": {"url": data_url}},
                ],
            }
        ],
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
        },
        method="POST",
    )
    started = time.time()
    try:
        with urllib.request.urlopen(req, timeout=VISION_API_TIMEOUT) as resp:
            data = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")[:300]
        raise RuntimeError(f"vision API HTTP {exc.code}: {body}") from exc

    choices = data.get("choices") or []
    if not choices:
        raise RuntimeError("vision API returned empty choices")
    content = (choices[0].get("message") or {}).get("content") or ""
    cleaned = clean_reply_text(content)
    if not cleaned:
        raise RuntimeError("vision API returned empty content")
    logger.info(
        "[image] vision via %s model=%s in %.1fs",
        cfg.source,
        cfg.model,
        time.time() - started,
    )
    set_cached_vision(digest, cleaned)
    return cleaned


def format_image_message(vision_text: str) -> str:
    """Raw parsed image text (direct reply formatting applied later)."""
    text = (vision_text or "").strip()
    if not text:
        return "（未能识别图片内容）"
    return text


def organize_document_text(raw_text: str) -> str:
    """Use text model to tidy long document extracts for direct reply."""
    from wx4py_mcp.workbuddy_model import resolve_workbuddy_model

    text = (raw_text or "").strip()
    if not text:
        return "（文档为空或无法读取）"
    if len(text) <= 600:
        return text
    try:
        resolved = resolve_workbuddy_model()
        url = f"{resolved.base_url.rstrip('/')}/chat/completions"
        payload = {
            "model": resolved.model,
            "messages": [
                {"role": "system", "content": DOCUMENT_TEXT_PROMPT},
                {"role": "user", "content": text[:12000]},
            ],
        }
        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {resolved.api_key}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=90) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        content = ((data.get("choices") or [{}])[0].get("message") or {}).get("content") or ""
        cleaned = clean_reply_text(content)
        return cleaned or text[:3000]
    except Exception as exc:
        logger.warning("[document] organize via text model failed: %s", exc)
        return text[:3000]
