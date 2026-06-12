#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""CLI: start WeChat private-chat auto-reply for one or more contacts."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from poll_private_chat import main as poll_main


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Listen to WeChat private chat and auto-reply (session list first, no search if visible)"
    )
    parser.add_argument("contacts", help="Contact remark name(s), comma-separated, e.g. Air or Air,娟子")
    parser.add_argument("--interval", type=float, default=15.0, help="Poll interval seconds")
    parser.add_argument("--once", action="store_true", help="Run one cycle and exit")
    parser.add_argument("--echo", action="store_true", help="Echo test mode (no AI)")
    args, rest = parser.parse_known_args()

    argv = [
        "poll_private_chat.py",
        "--contacts",
        args.contacts,
        "--interval",
        str(args.interval),
    ]
    if args.once:
        argv.append("--once")
    if args.echo:
        argv.append("--echo")
    else:
        argv.append("--workbuddy")
    argv.extend(rest)

    old_argv = sys.argv
    sys.argv = argv
    try:
        poll_main()
    finally:
        sys.argv = old_argv


if __name__ == "__main__":
    main()
