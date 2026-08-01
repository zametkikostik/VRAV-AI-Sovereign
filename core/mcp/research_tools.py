"""Register safe web research tools on MCP registry."""

from __future__ import annotations

from typing import Any, Dict, List

from core.mcp.protocol import mcp_registry
from core.research.web import web_research


@mcp_registry.tool(
    name="web_search",
    description="Search the public web for information (DuckDuckGo / Serper). Read-only research.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
)
async def web_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    return await web_research.search(query, max_results=int(max_results or 5))


@mcp_registry.tool(
    name="web_fetch",
    description="Fetch a public http(s) page as plain text (size-capped). Never executes scripts.",
    input_schema={
        "type": "object",
        "properties": {"url": {"type": "string"}},
        "required": ["url"],
    },
)
async def web_fetch(url: str) -> Dict[str, Any]:
    return await web_research.fetch(url)


@mcp_registry.tool(
    name="wiki_summary",
    description="Get a Wikipedia summary for a topic (safe structured API).",
    input_schema={
        "type": "object",
        "properties": {
            "title": {"type": "string"},
            "lang": {"type": "string", "default": "en"},
        },
        "required": ["title"],
    },
)
async def wiki_summary(title: str, lang: str = "en") -> Dict[str, Any]:
    return await web_research.wiki_summary(title, lang=lang or "en")
