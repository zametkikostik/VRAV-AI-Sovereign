"""MCP protocol unit tests."""

import pytest
from core.mcp.protocol import MCPToolRegistry, mcp_registry
import core.mcp.builtin_tools  # register


@pytest.mark.asyncio
async def test_tools_list_rpc():
    resp = await mcp_registry.handle_rpc(
        {"jsonrpc": "2.0", "id": 1, "method": "tools/list", "params": {}}
    )
    assert resp["id"] == 1
    names = [t["name"] for t in resp["result"]["tools"]]
    assert "echo" in names


@pytest.mark.asyncio
async def test_tools_call_echo():
    resp = await mcp_registry.handle_rpc(
        {"jsonrpc": "2.0", "id": 2, "method": "tools/call",
         "params": {"name": "echo", "arguments": {"message": "ping"}}}
    )
    assert resp.get("error") is None


@pytest.mark.asyncio
async def test_initialize():
    resp = await mcp_registry.handle_rpc(
        {"jsonrpc": "2.0", "id": 0, "method": "initialize", "params": {}}
    )
    assert resp["result"]["serverInfo"]["name"] == "vrav-mcp"


@pytest.mark.asyncio
async def test_custom_registry():
    reg = MCPToolRegistry()

    @reg.tool(name="add", description="add two numbers")
    async def add(a: int, b: int):
        return {"sum": int(a) + int(b)}

    result = await reg.call_tool("add", {"a": 2, "b": 3})
    assert result["sum"] == 5
