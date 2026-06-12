"""Singleton wx4py client (inspired by wxauto-mcp WeChatWrapper)."""

from __future__ import annotations

import threading
from typing import Optional

from wx4py import WeChatClient

_lock = threading.RLock()
_client: Optional[WeChatClient] = None


def get_client() -> WeChatClient:
    global _client
    with _lock:
        if _client is None:
            _client = WeChatClient()
            _client.connect()
        return _client


def reset_client() -> None:
    global _client
    with _lock:
        if _client is not None:
            try:
                _client.disconnect()
            except Exception:
                pass
            _client = None
