"""MCP RPC layer (pattern from wxauto-mcp)."""

from __future__ import annotations

import inspect
import logging
from functools import wraps
from typing import Any, Callable, Optional

from mcp.server import Server
from mcp.types import TextContent, Tool

logger = logging.getLogger(__name__)

MAX_OUTPUT_SIZE = 50000
MCP_SERVER = Server("wx4py-mcp")


class ToolRegistry:
    def __init__(self) -> None:
        self._tools: dict[str, dict[str, Any]] = {}

    def register(self, name: str, func: Callable, description: str = "") -> None:
        self._tools[name] = {"func": func, "description": description}

    def get_tool(self, name: str) -> Optional[dict[str, Any]]:
        return self._tools.get(name)

    def get_all_tools(self) -> dict[str, dict[str, Any]]:
        return dict(self._tools)


TOOL_REGISTRY = ToolRegistry()


def limit_output(func: Callable) -> Callable:
    @wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> str:
        result = func(*args, **kwargs)
        if isinstance(result, str) and len(result) > MAX_OUTPUT_SIZE:
            return result[:MAX_OUTPUT_SIZE] + f"\n... (truncated, was {len(result)} chars)"
        return result

    return wrapper


def tool(name: Optional[str] = None, description: Optional[str] = None) -> Callable:
    def decorator(func: Callable) -> Callable:
        limited = limit_output(func)
        tool_name = name or func.__name__
        TOOL_REGISTRY.register(tool_name, limited, description or (func.__doc__ or ""))
        return func

    return decorator


def _build_input_schema(func: Callable) -> dict[str, Any]:
    sig = inspect.signature(func)
    schema: dict[str, Any] = {"type": "object", "properties": {}}
    required = []
    for param_name, param in sig.parameters.items():
        param_type = "string"
        if param.annotation is int:
            param_type = "integer"
        elif param.annotation is bool:
            param_type = "boolean"
        elif param.annotation is float:
            param_type = "number"
        schema["properties"][param_name] = {"type": param_type}
        if param.default is inspect.Parameter.empty:
            required.append(param_name)
    if required:
        schema["required"] = required
    return schema


@MCP_SERVER.list_tools()
async def handle_list_tools() -> list[Tool]:
    tools = []
    for name, info in TOOL_REGISTRY.get_all_tools().items():
        func = info["func"]
        tools.append(
            Tool(
                name=name,
                description=info.get("description", ""),
                inputSchema=_build_input_schema(func),
            )
        )
    return tools


@MCP_SERVER.call_tool()
async def handle_call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
    info = TOOL_REGISTRY.get_tool(name)
    if not info:
        raise ValueError(f"unknown tool: {name}")
    result = info["func"](**arguments)
    if not isinstance(result, str):
        result = str(result)
    return [TextContent(type="text", text=result)]
