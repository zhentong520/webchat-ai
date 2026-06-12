"""Single-process / cross-process lock for WeChat UI automation."""

from __future__ import annotations

import contextlib
import logging
import msvcrt
import os
import threading
import time
from pathlib import Path

logger = logging.getLogger(__name__)

LOCK_FILE = Path.home() / ".wx4py-mcp" / "wechat.ui.lock"
LOCK_WAIT_SEC = 30.0
_local = threading.local()


def _depth() -> int:
    return int(getattr(_local, "depth", 0) or 0)


def _set_depth(value: int) -> None:
    _local.depth = value


@contextlib.contextmanager
def wechat_ui_lock(wait_sec: float = LOCK_WAIT_SEC):
    """Reentrant in one thread; exclusive across processes."""
    if _depth() > 0:
        _set_depth(_depth() + 1)
        try:
            yield
        finally:
            _set_depth(_depth() - 1)
        return

    LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
    handle = open(LOCK_FILE, "a+b")
    deadline = time.time() + wait_sec
    acquired = False
    while time.time() < deadline:
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_NBLCK, 1)
            acquired = True
            break
        except OSError:
            time.sleep(0.2)
    if not acquired:
        handle.close()
        raise TimeoutError(f"WeChat UI lock busy after {wait_sec}s: {LOCK_FILE}")

    _set_depth(1)
    try:
        handle.seek(0)
        handle.truncate()
        handle.write(str(os.getpid()).encode("ascii"))
        handle.flush()
        yield
    finally:
        _set_depth(0)
        try:
            handle.seek(0)
            msvcrt.locking(handle.fileno(), msvcrt.LK_UNLCK, 1)
        except OSError:
            pass
        handle.close()
