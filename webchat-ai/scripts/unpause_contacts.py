#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Clear __paused__ for contacts (used by listen-wechat.ps1)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wx4py_mcp.state_store import clear_pause

if __name__ == "__main__":
    names = [c.strip() for c in (sys.argv[1] if len(sys.argv) > 1 else "Air").split(",") if c.strip()]
    clear_pause(names)
    print(f"unpaused: {', '.join(names)}")
