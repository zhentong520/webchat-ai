#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Stop WeChat polling listeners (private / group).

Examples:
  python stop_listen.py --contacts coco
  python stop_listen.py --contacts Air,娟子
  python stop_listen.py --groups 测试群1
  python stop_listen.py --all-private
  python stop_listen.py --all
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wx4py_mcp.state_store import GROUP_STATE_FILE, DEFAULT_STATE_FILE, set_pause

PRIVATE_SCRIPT = "poll_private_chat.py"
GROUP_SCRIPT = "poll_group_chat.py"
CONTACTS_RE = re.compile(r"--contacts\s+(\S+)")
GROUPS_RE = re.compile(r"--groups\s+(\S+)")


def _iter_python_processes() -> list[tuple[int, str]]:
    ps = subprocess.run(
        [
            "powershell",
            "-NoProfile",
            "-Command",
            "Get-CimInstance Win32_Process -Filter \"Name='python.exe'\" "
            "| Select-Object ProcessId,CommandLine | ConvertTo-Json -Compress",
        ],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    stdout = ps.stdout or ""
    if ps.returncode != 0 or not stdout.strip():
        return []
    try:
        data = json.loads(stdout)
    except json.JSONDecodeError:
        return []
    if isinstance(data, dict):
        data = [data]
    rows: list[tuple[int, str]] = []
    for row in data:
        pid = row.get("ProcessId")
        cmd = row.get("CommandLine") or ""
        if pid is not None:
            rows.append((int(pid), cmd))
    return rows


def _parse_arg_list(cmdline: str, pattern: re.Pattern[str]) -> list[str]:
    match = pattern.search(cmdline)
    if not match:
        return []
    return [part.strip() for part in match.group(1).split(",") if part.strip()]


def _targets_match(running: list[str], wanted: list[str]) -> bool:
    if not wanted:
        return True
    wanted_set = set(wanted)
    return bool(wanted_set.intersection(running))


def find_listener_pids(
    script_name: str,
    targets: list[str] | None = None,
    arg_pattern: re.Pattern[str] | None = None,
) -> list[tuple[int, str, list[str]]]:
    """Return (pid, cmdline, running_targets) for matching listener processes."""
    hits: list[tuple[int, str, list[str]]] = []
    for pid, cmd in _iter_python_processes():
        if script_name not in cmd:
            continue
        running = _parse_arg_list(cmd, arg_pattern) if arg_pattern else []
        if targets is not None and arg_pattern is not None:
            if not _targets_match(running, targets):
                continue
        hits.append((pid, cmd, running))
    return hits


def kill_processes(pids: list[int]) -> list[int]:
    stopped: list[int] = []
    for pid in pids:
        result = subprocess.run(
            ["taskkill", "/PID", str(pid), "/F"],
            capture_output=True,
            text=True,
            check=False,
        )
        if result.returncode == 0:
            stopped.append(pid)
    return stopped


def stop_private(contacts: list[str] | None, pause: bool) -> int:
    targets = contacts
    hits = find_listener_pids(PRIVATE_SCRIPT, targets, CONTACTS_RE)
    pids = [pid for pid, _cmd, _names in hits]
    stopped = kill_processes(pids)

    paused_names: set[str] = set()
    if pause:
        if contacts:
            paused_names.update(contacts)
        else:
            for _pid, _cmd, names in hits:
                paused_names.update(names)
        if paused_names:
            set_pause(sorted(paused_names), DEFAULT_STATE_FILE, paused=True)

    for pid in stopped:
        print(f"stopped private listener PID {pid}")
    if pause and paused_names:
        print(f"paused contacts: {', '.join(sorted(paused_names))}")
    if not stopped and not paused_names:
        print("no private listener running")
    return 0 if stopped or not targets else 0


def stop_group(groups: list[str] | None, pause: bool) -> int:
    targets = groups
    hits = find_listener_pids(GROUP_SCRIPT, targets, GROUPS_RE)
    pids = [pid for pid, _cmd, _names in hits]
    stopped = kill_processes(pids)

    paused_names: set[str] = set()
    if pause:
        if groups:
            paused_names.update(groups)
        else:
            for _pid, _cmd, names in hits:
                paused_names.update(names)
        if paused_names:
            set_pause(sorted(paused_names), GROUP_STATE_FILE, paused=True)

    for pid in stopped:
        print(f"stopped group listener PID {pid}")
    if pause and paused_names:
        print(f"paused groups: {', '.join(sorted(paused_names))}")
    if not stopped and not paused_names:
        print("no group listener running")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="Stop WeChat AI polling listeners")
    parser.add_argument("--contacts", help="Private contacts (comma-separated). Omit with --all-private to stop all.")
    parser.add_argument("--groups", help="Group names (comma-separated). Omit with --all-groups to stop all.")
    parser.add_argument("--all-private", action="store_true", help="Stop all private listeners")
    parser.add_argument("--all-groups", action="store_true", help="Stop all group listeners")
    parser.add_argument("--all", action="store_true", help="Stop all private and group listeners")
    parser.add_argument("--no-pause", action="store_true", help="Kill process only, do not set paused state")
    args = parser.parse_args()

    pause = not args.no_pause
    exit_code = 0

    if args.all or args.all_private or args.contacts is not None:
        contacts = None
        if args.contacts:
            contacts = [c.strip() for c in args.contacts.split(",") if c.strip()]
        elif not args.all and not args.all_private:
            parser.error("use --contacts NAME, --all-private, or --all")
        stop_private(contacts, pause)

    if args.all or args.all_groups or args.groups is not None:
        groups = None
        if args.groups:
            groups = [g.strip() for g in args.groups.split(",") if g.strip()]
        elif not args.all and not args.all_groups:
            parser.error("use --groups NAME, --all-groups, or --all")
        stop_group(groups, pause)

    if not (args.all or args.all_private or args.all_groups or args.contacts or args.groups):
        stop_private(None, pause)
        stop_group(None, pause)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
