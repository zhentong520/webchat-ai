#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Start WeChat polling listeners from config/listen-defaults.json.

Examples:
  python start_listen.py --all
  python start_listen.py --private --contacts Air,coco
  python start_listen.py --groups 测试群1
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

from stop_listen import GROUP_SCRIPT, PRIVATE_SCRIPT, find_listener_pids, kill_processes

DEFAULTS_FILE = ROOT / "config" / "listen-defaults.json"


def _python_exe() -> str:
    env_py = Path(
        __import__("os").environ.get("LOCALAPPDATA", "")
    ) / "Programs/Python/Python311/python.exe"
    if env_py.exists():
        return str(env_py)
    alt = Path.home() / ".workbuddy/binaries/python/versions/3.13.12/python.exe"
    if alt.exists():
        return str(alt)
    return sys.executable


def _split_names(raw: str) -> list[str]:
    return [part.strip() for part in raw.replace("，", ",").split(",") if part.strip()]


def prompt_contacts() -> list[str]:
    print("=" * 42)
    print("  WebChat AI - 启动私聊监听")
    print("=" * 42)
    print("请输入微信备注名（多个用逗号分隔）")
    print("示例: Air,coco")
    print()
    raw = input("监听对象: ").strip()
    if not raw:
        print("[取消] 未输入联系人")
        return []
    contacts = _split_names(raw)
    print(f"\n即将监听: {', '.join(contacts)}")
    return contacts


def prompt_groups() -> list[str]:
    print()
    raw = input("是否监听群聊？输入群名（逗号分隔，直接回车跳过）: ").strip()
    if not raw:
        return []
    groups = _split_names(raw)
    print(f"即将监听群: {', '.join(groups)}")
    return groups


def load_defaults(path: Path = DEFAULTS_FILE) -> dict:
    if not path.exists():
        return {"interval": 15, "private_contacts": ["Air"], "groups": []}
    data = json.loads(path.read_text(encoding="utf-8"))
    return data if isinstance(data, dict) else {}


def _listener_running(script: str) -> bool:
    return bool(find_listener_pids(script, None, None))


def _run_unpause(script_rel: str, names: str) -> None:
    py = _python_exe()
    script = ROOT / "scripts" / script_rel
    subprocess.run([py, str(script), names], check=False, cwd=str(ROOT))


def _spawn_listener(title: str, script_rel: str, argv: list[str]) -> None:
    py = _python_exe()
    script = str(ROOT / "scripts" / script_rel)
    inner = subprocess.list2cmdline([py, script, *argv])
    subprocess.Popen(f'start "{title}" /MIN {inner}', shell=True, cwd=str(ROOT))


def send_welcome_messages(contacts: list[str]) -> None:
    """Open WeChat and send intro message to each contact before listening."""
    if not contacts:
        return
    from wx4py_mcp.client import get_client
    from wx4py_mcp.listen_control import WELCOME_MSG
    from wx4py_mcp.open_chat import send_message_smart

    print("正在发送自我介绍...")
    wx = get_client()
    for name in contacts:
        ok = send_message_smart(wx.chat_window, name, WELCOME_MSG, "contact")
        status = "已发送" if ok else "发送失败"
        print(f"  {name}: {status}")


def start_private(contacts: list[str], interval: float, force: bool, *, welcome: bool = False) -> bool:
    if not contacts:
        print("skip private: no contacts configured")
        return False
    if _listener_running(PRIVATE_SCRIPT):
        if not force:
            print("private listener already running (run stop-all.bat first or use --force)")
            return False
        pids = [pid for pid, _c, _n in find_listener_pids(PRIVATE_SCRIPT, None, None)]
        kill_processes(pids)

    joined = ",".join(contacts)
    _run_unpause("unpause_contacts.py", joined)
    if welcome:
        send_welcome_messages(contacts)
    _spawn_listener(
        f"WebChat-私聊-{joined}",
        "poll_private_chat.py",
        ["--contacts", joined, "--interval", str(interval), "--workbuddy"],
    )
    print(f"started private listener: {joined} (interval={interval}s)")
    return True


def start_groups(groups: list[str], interval: float, force: bool) -> bool:
    if not groups:
        print("skip groups: none configured")
        return False
    if _listener_running(GROUP_SCRIPT):
        if not force:
            print("group listener already running (run stop-all.bat first or use --force)")
            return False
        pids = [pid for pid, _c, _n in find_listener_pids(GROUP_SCRIPT, None, None)]
        kill_processes(pids)

    joined = ",".join(groups)
    _run_unpause("unpause_groups.py", joined)
    _spawn_listener(
        f"WebChat-群聊-{joined}",
        "poll_group_chat.py",
        ["--groups", joined, "--interval", str(interval), "--workbuddy"],
    )
    print(f"started group listener: {joined} (interval={interval}s)")
    return True


def main() -> int:
    parser = argparse.ArgumentParser(description="Start WeChat AI listeners")
    parser.add_argument("--all", action="store_true", help="Start from config/listen-defaults.json")
    parser.add_argument("--private", action="store_true", help="Start private only")
    parser.add_argument("--groups", action="store_true", help="Start groups only")
    parser.add_argument("--contacts", help="Override private contacts (comma-separated)")
    parser.add_argument("--group-names", help="Override group names (comma-separated)")
    parser.add_argument("--interval", type=float, help="Poll interval seconds")
    parser.add_argument("--force", action="store_true", help="Restart if already running")
    parser.add_argument("--interactive", "-i", action="store_true", help="Prompt for contact / group names")
    parser.add_argument("--welcome", action="store_true", help="Send AI intro message before listening")
    parser.add_argument("--no-welcome", action="store_true", help="Skip intro message")
    parser.add_argument("--config", default=str(DEFAULTS_FILE), help="Defaults JSON path")
    args = parser.parse_args()

    cfg = load_defaults(Path(args.config))
    interval = args.interval if args.interval is not None else float(cfg.get("interval", 15))
    welcome = args.welcome or (args.interactive and not args.no_welcome)

    if args.interactive:
        contacts = prompt_contacts()
        if not contacts:
            return 1
        groups = prompt_groups()
        started = start_private(contacts, interval, args.force, welcome=welcome)
        if groups:
            started = start_groups(groups, interval, args.force) or started
        if not started:
            print("nothing started")
            return 1
        return 0

    contacts = (
        [c.strip() for c in args.contacts.split(",") if c.strip()]
        if args.contacts
        else [str(c).strip() for c in cfg.get("private_contacts", []) if str(c).strip()]
    )
    groups = (
        [g.strip() for g in args.group_names.split(",") if g.strip()]
        if args.group_names
        else [str(g).strip() for g in cfg.get("groups", []) if str(g).strip()]
    )

    do_all = args.all or not (args.private or args.groups or args.contacts or args.group_names)
    started = False

    if do_all or args.private or args.contacts:
        started = start_private(contacts, interval, args.force, welcome=welcome) or started
    if do_all or args.groups or args.group_names:
        started = start_groups(groups, interval, args.force) or started

    if not started:
        print("nothing started")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
