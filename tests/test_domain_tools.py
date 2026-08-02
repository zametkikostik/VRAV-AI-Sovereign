"""Domain MCP tools (offline)."""
import asyncio
import core.mcp.domain_tools  # noqa: F401
from core.mcp.protocol import mcp_registry

def test_calc_safe():
    r = asyncio.get_event_loop().run_until_complete(
        mcp_registry.call_tool("calc", {"expression": "(2+3)*4"})
    )
    assert r["result"] == 20.0

def test_calc_rejects_code():
    r = asyncio.get_event_loop().run_until_complete(
        mcp_registry.call_tool("calc", {"expression": "__import__('os')"})
    )
    assert "error" in r

def test_datetime_now():
    r = asyncio.get_event_loop().run_until_complete(
        mcp_registry.call_tool("datetime_now", {})
    )
    assert "sofia" in r and "utc" in r

def test_ai_act_overview():
    r = asyncio.get_event_loop().run_until_complete(
        mcp_registry.call_tool("eu_ai_act_overview", {})
    )
    assert r["celex"] == "32024R1689"

def test_labor_hint():
    r = asyncio.get_event_loop().run_until_complete(
        mcp_registry.call_tool("bg_labor_code_hint", {"topic": "dismissal"})
    )
    assert "guidance" in r
