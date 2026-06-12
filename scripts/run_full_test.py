#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Automated wx4py-mcp full test runner — outputs JSON results."""

from __future__ import annotations

import json
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

RESULTS: list[dict] = []


def record(case_id: str, name: str, ok: bool | None, detail: str = "") -> None:
    RESULTS.append({"id": case_id, "name": name, "ok": ok, "detail": detail})
    if ok is None:
        mark = "MANUAL"
    else:
        mark = "PASS" if ok else "FAIL"
    print(f"[{mark}] {case_id} {name} — {detail}")


def phase_a_sends() -> None:
    from wx4py import WeChatClient
    from wx4py_mcp.open_chat import get_active_chat_title, is_chat_open_for, send_message_smart

    with WeChatClient() as wx:
        cw = wx.chat_window
        ok = send_message_smart(cw, "Air", "【测试1.1】私聊发送", "contact")
        record("1.1", "私聊发送 Air", ok)

        ok = send_message_smart(cw, "Air", "【测试1.2】切换发送", "contact")
        record("1.2", "切换后发送 Air", ok)

        ok = send_message_smart(cw, "测试群1", "【测试1.3】群聊发送", "group")
        record("1.3", "群聊发送 测试群1", ok)

        time.sleep(0.5)
        in_group = is_chat_open_for(cw, "测试群1")
        ok = send_message_smart(cw, "测试群1", "【测试1.4】已在群内直发", "group")
        record("1.4", "已在目标群直发", ok and in_group, f"in_group={in_group}")


def phase_private_listener() -> None:
    import subprocess

    py = sys.executable
    poll = ROOT / "scripts" / "poll_private_chat.py"
    unpause = ROOT / "scripts" / "unpause_contacts.py"

    subprocess.run([py, str(unpause), "Air"], check=False, capture_output=True)

    from wx4py import WeChatClient
    from wx4py_mcp.last_message import get_last_chat_line
    from wx4py_mcp.open_chat import send_message_smart

    tag = f"【测试2.4-{int(time.time())}】"
    with WeChatClient() as wx:
        send_message_smart(wx.chat_window, "Air", tag, "contact")

    r = subprocess.run(
        [py, str(poll), "--contacts", "Air", "--echo", "--once"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    out = r.stdout + r.stderr
    record("2.4", "私聊跳过自己消息", "replied once" not in out, "poll --once after self send")

    with WeChatClient() as wx:
        last = get_last_chat_line(wx.chat_window, "Air", "contact")
    if last and last.get("from_peer"):
        r2 = subprocess.run(
            [py, str(poll), "--contacts", "Air", "--workbuddy", "--once"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        out2 = r2.stdout + r2.stderr
        ai_ok = "replied once" in out2
        record("2.2", "私聊 AI 回复(peer最后一条)", ai_ok, (last.get("content") or "")[:40])
    else:
        record("2.2", "私聊 AI 回复(peer最后一条)", False, "最后一条非 Air 消息，需 Air 发一条后重测")

    r3 = subprocess.run(
        [py, str(poll), "--contacts", "Air", "--workbuddy", "--once"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    out3 = r3.stdout + r3.stderr
    record("2.3", "私聊不重复回复", "Handled 0" in out3 or out3.count("replied once") == 0, "second --once")

    r4 = subprocess.run(
        [py, str(poll), "--contacts", "Air", "--workbuddy", "--once"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    record("2.1", "私聊监听启动", r4.returncode == 0 and "Polling contacts" in (r4.stdout + r4.stderr))

    record("2.5", "私聊停止监听", None, "需 Air 发「停止监听」— 见手动项")
    record("2.6", "私聊重启监听", None, "停止后重新 listen-wechat.ps1 — 见手动项")
    record("2.7", "私聊视频通话", None, "可选：Air 发「视频通话」")
    record("2.8", "私聊语音通话", None, "可选：Air 发「语音通话」")


def phase_group_listener() -> None:
    import subprocess

    py = sys.executable
    poll = ROOT / "scripts" / "poll_group_chat.py"
    unpause = ROOT / "scripts" / "unpause_groups.py"

    subprocess.run([py, str(unpause), "测试群1"], check=False, capture_output=True)

    from wx4py import WeChatClient
    from wx4py_mcp.last_message import get_last_chat_line
    from wx4py_mcp.open_chat import send_message_smart

    tag = f"【测试3.3-{int(time.time())}】"
    with WeChatClient() as wx:
        send_message_smart(wx.chat_window, "测试群1", tag, "group")

    r = subprocess.run(
        [py, str(poll), "--groups", "测试群1", "--echo", "--once"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    no_self_reply = "replied once" not in (r.stdout + r.stderr) or tag not in (r.stdout + r.stderr)
    record("3.3", "群聊跳过自己消息", no_self_reply or "Handled 0" in (r.stdout + r.stderr))

    with WeChatClient() as wx:
        last = get_last_chat_line(wx.chat_window, "测试群1", "group")
    if last and last.get("from_peer"):
        r2 = subprocess.run(
            [py, str(poll), "--groups", "测试群1", "--workbuddy", "--once"],
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
        )
        ai_ok = "replied once" in (r2.stdout + r2.stderr)
        record("3.2", "群聊 AI 回复(peer最后一条)", ai_ok, (last.get("content") or "")[:40])
    else:
        record("3.2", "群聊 AI 回复", False, "skip: 最后一条非群友消息，需在群里让别人发一条")

    r3 = subprocess.run(
        [py, str(poll), "--groups", "测试群1", "--workbuddy", "--once"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=90,
    )
    record("3.1", "群聊监听启动", r3.returncode == 0, "poll --once")
    record("3.4", "群聊停止监听", None, "需群友发「停止监听」— 见手动项")
    record("3.5", "群聊重启", None, "listen-wechat-group.ps1 — 见手动项")


def phase_stress() -> None:
    import subprocess

    py = sys.executable
    stress = ROOT / "scripts" / "stress_test_session.py"
    r = subprocess.run(
        [py, str(stress), "--case", "all"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=300,
    )
    out = r.stdout + r.stderr
    passed_n = out.count(" OK ") + out.count("summary")
    record("4.x", "stress_test_session all", r.returncode == 0, out.split("summary")[-1][:80] if "summary" in out else out[-120:])


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    print("=== Phase A: sends ===")
    phase_a_sends()
    print("\n=== Phase B: private listener ===")
    phase_private_listener()
    print("\n=== Phase D: group listener ===")
    phase_group_listener()
    print("\n=== Phase E: stress ===")
    phase_stress()

    out = Path.home() / ".wx4py-mcp" / "full-test-results.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(RESULTS, ensure_ascii=False, indent=2), encoding="utf-8")
    passed = sum(1 for x in RESULTS if x["ok"] is True)
    failed = sum(1 for x in RESULTS if x["ok"] is False)
    manual = sum(1 for x in RESULTS if x["ok"] is None)
    print(f"\n=== SUMMARY pass={passed} fail={failed} manual={manual} ===")
    print(f"Results: {out}")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
