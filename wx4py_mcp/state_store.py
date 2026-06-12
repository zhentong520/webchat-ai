"""Private listener state: load/save with schema cleanup."""

from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

STATE_SUFFIXES = ("__paused__", "__last_replied__", "__outgoing__")
DEFAULT_STATE_DIR = Path.home() / ".wx4py-mcp"
DEFAULT_STATE_FILE = DEFAULT_STATE_DIR / "private_seen.json"


def normalize_state(raw: dict[str, Any]) -> dict[str, Any]:
    """Keep only listener keys; drop legacy contact -> list history."""
    clean: dict[str, Any] = {}
    dropped = 0
    for key, value in raw.items():
        if any(key.endswith(suffix) for suffix in STATE_SUFFIXES):
            clean[key] = value
        else:
            dropped += 1
    if dropped:
        logger.info("[state] dropped %s legacy keys", dropped)
    return clean


def load_state(path: Path = DEFAULT_STATE_FILE) -> dict[str, Any]:
    if not path.exists():
        return {}
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[state] load failed, reset: %s", exc)
        return {}
    if not isinstance(raw, dict):
        return {}
    return normalize_state(raw)


def save_state(state: dict[str, Any], path: Path = DEFAULT_STATE_FILE) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    clean = normalize_state(state)
    path.write_text(json.dumps(clean, ensure_ascii=False, indent=2), encoding="utf-8")


def clear_pause(contacts: list[str], path: Path = DEFAULT_STATE_FILE) -> None:
    set_pause(contacts, path, paused=False)


def set_pause(contacts: list[str], path: Path = DEFAULT_STATE_FILE, *, paused: bool = True) -> None:
    state = load_state(path)
    for name in contacts:
        name = name.strip()
        if not name:
            continue
        state[f"{name}__paused__"] = paused
    save_state(state, path)


GROUP_STATE_FILE = DEFAULT_STATE_DIR / "group_seen.json"
