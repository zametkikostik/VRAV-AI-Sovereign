"""Sandbox MCP tool — safe code execution with whitelist."""

from __future__ import annotations

from typing import Any, Dict

from core.mcp.protocol import mcp_registry
from core.sandbox.runner import sandbox


@mcp_registry.tool(
    name="code_sandbox",
    description=(
        "Execute short pure-Python snippets in a restricted sandbox. "
        "Allowed: math, json, re, datetime, collections, statistics, decimal. "
        "No network, no filesystem, no subprocess."
    ),
    input_schema={
        "type": "object",
        "properties": {"code": {"type": "string", "description": "Python source"}},
        "required": ["code"],
    },
)
async def code_sandbox(code: str) -> Dict[str, Any]:
    return sandbox.run(code)
