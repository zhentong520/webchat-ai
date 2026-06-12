"""Shared helpers."""

import json
from typing import Any, Optional


def format_result(success: bool, message: str, data: Optional[dict[str, Any]] = None) -> str:
    return json.dumps(
        {"success": success, "message": message, "data": data or {}},
        ensure_ascii=False,
        indent=2,
    )
