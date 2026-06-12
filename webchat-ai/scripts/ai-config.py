#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Init or show project AI config (config/ai-config.json)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wx4py_mcp.ai_config import AI_CONFIG_FILE, config_status, save_ai_config_template


def main() -> int:
    parser = argparse.ArgumentParser(description="WebChat AI model config helper")
    parser.add_argument("--init", action="store_true", help="Create ai-config.json from example")
    parser.add_argument("--status", action="store_true", help="Show config status (default)")
    parser.add_argument("--list", action="store_true", help="List profiles and _description comments")
    args = parser.parse_args()

    if args.init:
        path = save_ai_config_template()
        print(f"Created: {path}")
        print("Edit api_key in config/ai-config.json")

    if args.list:
        from wx4py_mcp.ai_config import _read_json, AI_CONFIG_FILE
        data = _read_json(AI_CONFIG_FILE) or {}
        print("=== 默认 ===")
        if data.get("_description"):
            print(f"  {data['_description']}")
        if data.get("_fields"):
            print("  字段:", json.dumps(data["_fields"], ensure_ascii=False))
        print(f"  model: {data.get('model')} @ {data.get('base_url')}")
        print("\n=== profiles ===")
        for name, block in (data.get("profiles") or {}).items():
            if not isinstance(block, dict):
                continue
            desc = block.get("_description", "(无说明)")
            print(f"  [{name}] {desc}")
            print(f"         model={block.get('model')} key={'已填' if block.get('api_key') else '未填'}")
        active = data.get("active_profile") or "(default)"
        print(f"\nactive_profile: {active}")
        return 0

    status = config_status()
    print(json.dumps(status, ensure_ascii=False, indent=2))
    return 0 if status.get("configured") or args.init else 1


if __name__ == "__main__":
    raise SystemExit(main())
