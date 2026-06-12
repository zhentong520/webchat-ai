#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Clear __paused__ for groups (used by listen-wechat-group.ps1)."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wx4py_mcp.state_store import GROUP_STATE_FILE, clear_pause

if __name__ == "__main__":
    names = [g.strip() for g in (sys.argv[1] if len(sys.argv) > 1 else "测试群1").split(",") if g.strip()]
    clear_pause(names, GROUP_STATE_FILE)
    print(f"unpaused groups: {', '.join(names)}")
