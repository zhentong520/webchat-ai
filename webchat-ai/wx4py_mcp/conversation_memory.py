"""Per-user local conversation memory for AI context (isolated JSON files)."""

from __future__ import annotations

import json
import logging
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)

MEMORY_DIR = Path(os.getenv("WX4PY_STATE_DIR", str(Path.home() / ".wx4py-mcp"))) / "memory"
MAX_MEMORY_MESSAGES = int(os.getenv("WX4PY_MEMORY_SIZE", "10"))
INVALID_FS_CHARS = re.compile(r'[<>:"/\\|?*\x00-\x1f]')


def is_memory_enabled() -> bool:
    return MAX_MEMORY_MESSAGES > 0


def _now_iso() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def _safe_target_filename(target: str) -> str:
    name = (target or "unknown").strip()
    safe = INVALID_FS_CHARS.sub("_", name)
    return safe or "unknown"


def memory_file_path(target: str, target_type: str) -> Path:
    sub = "private" if target_type == "contact" else "group"
    return MEMORY_DIR / sub / f"{_safe_target_filename(target)}.json"


def _empty_record(target: str, target_type: str) -> dict[str, Any]:
    return {
        "target": target,
        "target_type": target_type,
        "max_messages": MAX_MEMORY_MESSAGES,
        "updated_at": _now_iso(),
        "messages": [],
    }


def load_memory(target: str, target_type: str) -> list[dict[str, str]]:
    """Return stored messages: [{role, content, time?}, ...]."""
    if not is_memory_enabled():
        return []
    path = memory_file_path(target, target_type)
    if not path.exists():
        return []
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except Exception as exc:
        logger.warning("[memory] load failed %s: %s", path.name, exc)
        return []
    if not isinstance(data, dict):
        return []
    messages = data.get("messages")
    if not isinstance(messages, list):
        return []
    out: list[dict[str, str]] = []
    for item in messages:
        if not isinstance(item, dict):
            continue
        role = (item.get("role") or "").strip()
        content = (item.get("content") or "").strip()
        if role in ("user", "assistant") and content:
            out.append({"role": role, "content": content})
    return out[-MAX_MEMORY_MESSAGES:]


def save_memory(target: str, target_type: str, messages: list[dict[str, str]]) -> None:
    if not is_memory_enabled():
        return
    path = memory_file_path(target, target_type)
    path.parent.mkdir(parents=True, exist_ok=True)
    trimmed = messages[-MAX_MEMORY_MESSAGES:]
    record = _empty_record(target, target_type)
    record["messages"] = [{**m, "time": m.get("time") or _now_iso()} for m in trimmed]
    record["updated_at"] = _now_iso()
    path.write_text(json.dumps(record, ensure_ascii=False, indent=2), encoding="utf-8")
    logger.info("[memory] saved %s (%s msgs)", path.name, len(trimmed))


def append_exchange(
    target: str,
    target_type: str,
    user_content: str,
    assistant_content: str,
) -> None:
    """Append one user/assistant pair; keep last N messages per target."""
    if not is_memory_enabled():
        return
    user_text = (user_content or "").strip()
    assistant_text = (assistant_content or "").strip()
    if not user_text or not assistant_text:
        return
    messages = load_memory(target, target_type)
    messages.append({"role": "user", "content": user_text})
    messages.append({"role": "assistant", "content": assistant_text})
    save_memory(target, target_type, messages)


def format_user_message(target: str, target_type: str, content: str) -> str:
    text = (content or "").strip()
    if target_type == "group":
        return f"群「{target}」里有人说：{text}"
    return f"{target}说：{text}"


def build_messages_with_memory(
    target: str,
    target_type: str,
    user_content: str,
) -> list[dict[str, str]]:
    """Build OpenAI-style messages: history + current user turn."""
    messages: list[dict[str, str]] = []
    for item in load_memory(target, target_type):
        role = item["role"]
        if role == "user":
            messages.append(
                {
                    "role": "user",
                    "content": format_user_message(target, target_type, item["content"]),
                }
            )
        else:
            messages.append({"role": "assistant", "content": item["content"]})
    messages.append(
        {
            "role": "user",
            "content": format_user_message(target, target_type, user_content),
        }
    )
    return messages


def clear_memory(target: str, target_type: str) -> None:
    path = memory_file_path(target, target_type)
    if path.exists():
        path.unlink(missing_ok=True)
        logger.info("[memory] cleared %s", path.name)
