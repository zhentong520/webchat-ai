"""Test voice/video call UI flow (does not confirm callee picks up)."""

from __future__ import annotations

import argparse
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    stream=sys.stdout,
)

from wx4py_mcp.call_control import start_video_call, start_voice_call
from wx4py_mcp.client import get_client


def main() -> int:
    parser = argparse.ArgumentParser(description="Test WeChat voice/video call")
    parser.add_argument("target", help="Contact or group name")
    parser.add_argument(
        "--type",
        choices=("voice", "video"),
        default="video",
        help="Call type (default: video)",
    )
    args = parser.parse_args()

    wx = get_client()
    if args.type == "voice":
        ok = start_voice_call(wx.chat_window, args.target)
    else:
        ok = start_video_call(wx.chat_window, args.target)

    print("OK" if ok else "FAIL")
    return 0 if ok else 1


if __name__ == "__main__":
    raise SystemExit(main())
