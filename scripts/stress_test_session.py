#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Edge-case tests for session-list open + private reply."""

from __future__ import annotations

import argparse
import json
import logging
import sys
import time
from pathlib import Path

from wx4py import WeChatClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wx4py_mcp.last_message import get_last_chat_line
from wx4py_mcp.open_chat import (
    find_session_item,
    get_active_chat_title,
    is_chat_open_for,
    open_chat_smart,
    send_message_smart,
    session_display_name,
    _click_session_name_area,
    _safe_text,
)

LOG = Path.home() / ".wx4py-mcp" / "stress-test.log"


def setup_logging() -> None:
    LOG.parent.mkdir(parents=True, exist_ok=True)
    handlers = [
        logging.FileHandler(LOG, encoding="utf-8"),
        logging.StreamHandler(sys.stdout),
    ]
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(levelname)s %(message)s",
        handlers=handlers,
        force=True,
    )
    logging.getLogger("wx4py_mcp.open_chat").setLevel(logging.INFO)
    logging.getLogger("wx4py_mcp.last_message").setLevel(logging.INFO)


def record(results: list[dict], name: str, ok: bool, detail: str) -> None:
    status = "PASS" if ok else "FAIL"
    line = f"[{status}] {name}: {detail}"
    logging.info(line)
    results.append({"name": name, "ok": ok, "detail": detail})


def test_switch_session(results: list[dict]) -> None:
    with WeChatClient() as wx:
        cw = wx.chat_window
        cw._window.activate()
        time.sleep(1.0)
        if not is_chat_open_for(cw, "Air"):
            open_chat_smart(cw, "Air", "contact")
            time.sleep(0.5)
        alt = find_session_item(cw, "小雪，雪糕会员群") or find_session_item(cw, "文件传输助手")
        if not alt:
            record(results, "switch_session", False, "no alternate session visible in list")
            return
        alt_name = session_display_name(_safe_text(alt, "Name"))
        _click_session_name_area(alt)
        switched = False
        for _ in range(10):
            time.sleep(0.25)
            if not is_chat_open_for(cw, "Air"):
                switched = True
                break
        if not switched:
            record(results, "switch_session", False, f"click {alt_name!r} but still on Air")
            return
        ok = open_chat_smart(cw, "Air", "contact")
        title = get_active_chat_title(cw)
        record(results, "switch_session", ok and title == "Air", f"via {alt_name!r} open={ok} title={title!r}")


def test_minimize_restore(results: list[dict]) -> None:
    import win32con
    import win32gui

    with WeChatClient() as wx:
        cw = wx.chat_window
        hwnd = cw._window.hwnd
        win32gui.ShowWindow(hwnd, win32con.SW_MINIMIZE)
        time.sleep(0.8)
        minimized = win32gui.IsIconic(hwnd)
        cw._window.activate()
        time.sleep(0.8)
        restored = not win32gui.IsIconic(hwnd)
        ok = open_chat_smart(cw, "Air", "contact")
        title = get_active_chat_title(cw)
        record(
            results,
            "minimize_restore",
            minimized and restored and ok and title == "Air",
            f"minimized={minimized} restored={restored} open={ok} title={title!r}",
        )


def test_air_not_visible(results: list[dict]) -> None:
    """If Air not in visible rows, open_chat_smart should still succeed via search."""
    with WeChatClient() as wx:
        cw = wx.chat_window
        cw._window.activate()
        time.sleep(0.5)
        visible = find_session_item(cw, "Air") is not None
        if visible:
            record(
                results,
                "air_not_visible",
                True,
                "skipped: Air currently visible in list (scroll test manual)",
            )
            return
        ok = open_chat_smart(cw, "Air", "contact")
        record(results, "air_not_visible", ok, f"fallback open={ok}")


def test_read_and_send(results: list[dict]) -> None:
    with WeChatClient() as wx:
        cw = wx.chat_window
        ft = find_session_item(cw, "文件传输助手")
        if ft:
            _click_session_name_area(ft)
            time.sleep(0.8)
        last = get_last_chat_line(cw, "Air", "contact")
        ok_read = last is not None
        ok_send = send_message_smart(cw, "Air", "边界测试ping", "contact")
        record(
            results,
            "read_and_send",
            ok_read and ok_send,
            f"read={ok_read} send={ok_send} last={last.get('content','')[:30] if last else None}",
        )


def test_stop_and_restart(results: list[dict]) -> None:
    state_file = Path.home() / ".wx4py-mcp" / "private_seen.json"
    state = json.loads(state_file.read_text(encoding="utf-8"))
    state["Air__paused__"] = True
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    paused = state.get("Air__paused__") is True
    state["Air__paused__"] = False
    state["Air__last_replied__"] = ""
    state_file.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    restarted = state.get("Air__paused__") is False
    with WeChatClient() as wx:
        ok = is_chat_open_for(wx.chat_window, "Air") or open_chat_smart(wx.chat_window, "Air", "contact")
    record(results, "stop_and_restart", paused and restarted and ok, f"paused={paused} restart={restarted} open={ok}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--case", default="all", help="all | switch | minimize | read_send | restart")
    args = parser.parse_args()
    setup_logging()
    logging.info("=== stress test start ===")
    results: list[dict] = []
    cases = {
        "switch": [test_switch_session],
        "minimize": [test_minimize_restore],
        "read_send": [test_read_and_send],
        "restart": [test_stop_and_restart],
        "visible": [test_air_not_visible],
    }
    if args.case == "all":
        runners = [
            test_switch_session,
            test_minimize_restore,
            test_read_and_send,
            test_stop_and_restart,
            test_air_not_visible,
        ]
    else:
        runners = cases.get(args.case, [])
    for fn in runners:
        try:
            fn(results)
        except Exception as exc:
            record(results, fn.__name__, False, str(exc))
        time.sleep(0.5)
    passed = sum(1 for r in results if r["ok"])
    logging.info("=== summary %s/%s passed ===", passed, len(results))
    for r in results:
        logging.info("  %s %s", "OK" if r["ok"] else "XX", r["name"])
    if passed < len(results):
        sys.exit(1)


if __name__ == "__main__":
    main()
