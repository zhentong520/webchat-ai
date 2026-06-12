#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Mark current last peer line as handled."""

import json
import sys
from pathlib import Path

from wx4py import WeChatClient

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from wx4py_mcp.last_message import get_last_chat_line
from wx4py_mcp.listen_control import paused_key
from wx4py_mcp.state_store import DEFAULT_STATE_FILE, load_state, save_state

STATE = DEFAULT_STATE_FILE
LAST_REPLIED_SUFFIX = "__last_replied__"


def seed(contacts: list[str], out: Path) -> None:
    state = load_state(out)

    with WeChatClient() as wx:
        for contact in contacts:
            last_msg = get_last_chat_line(wx.chat_window, contact, "contact")
            last_replied = ""
            if last_msg and last_msg.get("from_peer") and (last_msg.get("content") or "").strip():
                content = last_msg["content"].strip()
                last_replied = f"{last_msg.get('time', '')}|{content}"
            state[f"{contact}{LAST_REPLIED_SUFFIX}"] = last_replied
            if paused_key(contact) not in state:
                state[paused_key(contact)] = False
            print(f"{contact}: last_replied={'set' if last_replied else 'empty'}")

    save_state(state, out)
    print(f"saved -> {out}")


if __name__ == "__main__":
    names = [c.strip() for c in (sys.argv[1] if len(sys.argv) > 1 else "Air").split(",") if c.strip()]
    seed(names, STATE)
