"""Resolve AI credentials: project config → env → WorkBuddy / mmx / OpenClaw."""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass
from pathlib import Path

from wx4py_mcp.ai_config import load_ai_config

THINKING_RE = re.compile(r"<think>.*?</think>", re.DOTALL | re.IGNORECASE)
THINKING_OPEN_RE = re.compile(r"<think>.*", re.DOTALL | re.IGNORECASE)

DEFAULT_BASE = "https://api.minimaxi.com/v1"
DEFAULT_MODEL = "MiniMax-M2.5"
PRIVATE_SYSTEM_PROMPT = (
    "你在微信私聊里回复朋友的消息。"
    "要求：自然简短、像真人聊天；不要说是 AI；不要加「收到：」前缀；1-3 句话即可。"
)
GROUP_SYSTEM_PROMPT = (
    "你在微信群聊里回复群友的消息。"
    "要求：自然简短、像真人聊天；不要说是 AI；不要加「收到：」前缀；1-3 句话即可。"
)


@dataclass
class ResolvedModel:
    base_url: str
    model: str
    api_key: str
    api_format: str = "completions"
    source: str = ""


def _read_json(path: Path) -> dict | list | None:
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def _normalize_base(url: str) -> str:
    base = (url or DEFAULT_BASE).strip().rstrip("/")
    for suffix in ("/chat/completions", "/v1/chat/completions"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base.rstrip("/")


def _from_workbuddy_models() -> ResolvedModel | None:
    data = _read_json(Path.home() / ".workbuddy" / "models.json")
    if not isinstance(data, list) or not data:
        return None
    item = data[0]
    if not isinstance(item, dict):
        return None
    api_key = (item.get("apiKey") or "").strip()
    if not api_key:
        return None
    return ResolvedModel(
        base_url=_normalize_base(item.get("url") or DEFAULT_BASE),
        model=(item.get("id") or item.get("name") or DEFAULT_MODEL).strip(),
        api_key=api_key,
        source="workbuddy/models.json",
    )


def _from_mmx() -> ResolvedModel | None:
    data = _read_json(Path.home() / ".mmx" / "config.json")
    if not isinstance(data, dict):
        return None
    api_key = (data.get("api_key") or "").strip()
    if not api_key:
        return None
    wb = _from_workbuddy_models()
    model = wb.model if wb else DEFAULT_MODEL
    return ResolvedModel(
        base_url=DEFAULT_BASE,
        model=model,
        api_key=api_key,
        source="mmx/config.json",
    )


def _from_openclaw() -> ResolvedModel | None:
    data = _read_json(Path.home() / ".openclaw" / "openclaw.json")
    if not isinstance(data, dict):
        return None
    providers = (data.get("models") or {}).get("providers") or {}
    minimax = providers.get("minimax") or {}
    api_key = (minimax.get("apiKey") or "").strip()
    if not api_key:
        return None
    base = _normalize_base(minimax.get("baseUrl") or DEFAULT_BASE)
    if base.endswith("/anthropic/v1"):
        base = DEFAULT_BASE
    models = minimax.get("models") or []
    model = DEFAULT_MODEL
    for item in models:
        if isinstance(item, dict) and item.get("id"):
            model = item["id"]
            break
    return ResolvedModel(
        base_url=base,
        model=model,
        api_key=api_key,
        source="openclaw/minimax",
    )


def resolve_workbuddy_model(prefer: str = "") -> ResolvedModel:
    """Pick the first usable model config on this machine."""
    if os.getenv("WX4PY_AI_API_KEY"):
        return ResolvedModel(
            base_url=_normalize_base(os.getenv("WX4PY_AI_BASE_URL", DEFAULT_BASE)),
            model=os.getenv("WX4PY_AI_MODEL", DEFAULT_MODEL),
            api_key=os.getenv("WX4PY_AI_API_KEY", ""),
            api_format=os.getenv("WX4PY_AI_API_FORMAT", "completions"),
            source="env",
        )

    project = load_ai_config()
    if project:
        return ResolvedModel(
            base_url=project.base_url,
            model=project.model,
            api_key=project.api_key,
            api_format=project.api_format,
            source=project.source,
        )

    fns = {
        "mmx": _from_mmx,
        "openclaw": _from_openclaw,
        "workbuddy": _from_workbuddy_models,
    }
    order = ["mmx", "openclaw", "workbuddy"]
    if prefer in fns:
        order = [prefer] + [name for name in order if name != prefer]

    for name in order:
        item = fns[name]()
        if item:
            return item

    raise RuntimeError(
        "未找到可用 AI 配置。请填写 E:/webchat-ai/config/ai-config.json，"
        "或设置 WX4PY_AI_* 环境变量，或配置 WorkBuddy/mmx。"
    )


def clean_reply_text(text: str) -> str:
    cleaned = THINKING_RE.sub("", text or "")
    cleaned = THINKING_OPEN_RE.sub("", cleaned)
    return cleaned.strip().strip("\"'")
