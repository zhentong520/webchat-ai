"""MCP server entry."""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys

from mcp.server.stdio import stdio_server

from . import api_messages  # noqa: F401
from . import api_system  # noqa: F401
from .rpc import MCP_SERVER

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    stream=sys.stderr,
)
logger = logging.getLogger(__name__)


async def run_stdio() -> None:
    async with stdio_server() as (read_stream, write_stream):
        await MCP_SERVER.run(read_stream, write_stream, MCP_SERVER.create_initialization_options())


def main() -> None:
    parser = argparse.ArgumentParser(description="wx4py MCP Server")
    parser.add_argument("--transport", choices=["stdio"], default="stdio")
    parser.add_argument("--log-level", default="INFO")
    args = parser.parse_args()
    logging.getLogger().setLevel(args.log_level.upper())
    if args.transport == "stdio":
        asyncio.run(run_stdio())


if __name__ == "__main__":
    main()
