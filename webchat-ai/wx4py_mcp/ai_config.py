"""Project-level AI model API config — shared by WebChat AI and other apps."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path

DEFAULT_BASE = "https://api.minimaxi.com/v1"
DEFAULT_MODEL = "MiniMax-M2.5"

# 项目根目录：E:/webchat-ai
PROJECT_ROOT = Path(__file__).resolve().parents[1]
CONFIG_DIR = PROJECT_ROOT / "config"
AI_CONFIG_FILE = CONFIG_DIR / "ai-config.json"
AI_CONFIG_EXAMPLE = CONFIG_DIR / "ai-config.example.json"


@dataclass
class AiConfig:
    base_url: str
    model: str
    api_key: str
    api_format: str = "completions"
    source: str = ""
    profile: str = ""


def _normalize_base(url: str) -> str:
    base = (url or DEFAULT_BASE).strip().rstrip("/")
    for suffix in ("/chat/completions", "/v1/chat/completions"):
        if base.endswith(suffix):
            base = base[: -len(suffix)]
    return base.rstrip("/")


def _read_json(path: Path) -> dict | None:
    if not path.exists():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def _block_to_config(block: dict, source: str, profile: str = "") -> AiConfig | None:
    api_key = (block.get("api_key") or block.get("apiKey") or "").strip()
    if not api_key:
        return None
    return AiConfig(
        base_url=_normalize_base(block.get("base_url") or block.get("baseUrl") or DEFAULT_BASE),
        model=(block.get("model") or block.get("id") or DEFAULT_MODEL).strip(),
        api_key=api_key,
        api_format=(block.get("api_format") or "completions").strip(),
        source=source,
        profile=profile,
    )


def load_ai_config(
    config_path: Path | None = None,
    profile: str | None = None,
) -> AiConfig | None:
    """
    Load AI config from project config/ai-config.json.

    Priority inside file: profile param > active_profile > top-level fields.
    Returns None if file missing or api_key empty.
    """
    path = Path(config_path) if config_path else AI_CONFIG_FILE
    if os.getenv("WEBCHAT_AI_CONFIG"):
        path = Path(os.getenv("WEBCHAT_AI_CONFIG"))

    data = _read_json(path)
    if not data:
        return None

    profiles = data.get("profiles") or {}
    active = (profile or data.get("active_profile") or "").strip()

    if active and isinstance(profiles.get(active), dict):
        item = _block_to_config(profiles[active], source=f"config/ai-config.json#{active}", profile=active)
        if item:
            return item

    item = _block_to_config(data, source="config/ai-config.json")
    if item:
        return item
    return None


def save_ai_config_template() -> Path:
    """Copy example to ai-config.json if not exists."""
    if AI_CONFIG_FILE.exists():
        return AI_CONFIG_FILE
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    if AI_CONFIG_EXAMPLE.exists():
        AI_CONFIG_FILE.write_text(AI_CONFIG_EXAMPLE.read_text(encoding="utf-8"), encoding="utf-8")
    else:
        AI_CONFIG_FILE.write_text(
            json.dumps(
                {
                    "base_url": DEFAULT_BASE,
                    "model": DEFAULT_MODEL,
                    "api_key": "",
                    "api_format": "completions",
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
    return AI_CONFIG_FILE


def config_status() -> dict:
    """Summary for CLI / docs — never exposes full api_key."""
    cfg = load_ai_config()
    if not cfg:
        exists = AI_CONFIG_FILE.exists()
        return {
            "configured": False,
            "path": str(AI_CONFIG_FILE),
            "exists": exists,
            "hint": "复制 config/ai-config.example.json 为 config/ai-config.json 并填写 api_key",
        }
    key = cfg.api_key
    masked = f"{key[:4]}...{key[-4:]}" if len(key) > 8 else "****"
    return {
        "configured": True,
        "path": str(AI_CONFIG_FILE),
        "source": cfg.source,
        "profile": cfg.profile or "(default)",
        "base_url": cfg.base_url,
        "model": cfg.model,
        "api_key_masked": masked,
    }
