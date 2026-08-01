"""Register built-in VRAV tools on the MCP registry."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from core.mcp.protocol import mcp_registry
from core.tools.eurlex import eurlex_client
from core.tools.cellar_sparql import cellar
from core.memory.store import memory_store
from core.skills.manager import skill_manager


@mcp_registry.tool(
    name="eurlex_get",
    description="Fetch EU legal document text by CELEX number (e.g. 32016R0679 for GDPR).",
    input_schema={
        "type": "object",
        "properties": {
            "celex": {"type": "string", "description": "CELEX identifier"},
            "language": {"type": "string", "description": "bg|en|de|fr", "default": "en"},
        },
        "required": ["celex"],
    },
)
async def eurlex_get(celex: str, language: str = "en") -> Dict[str, Any]:
    return await eurlex_client.get_by_celex(celex, language=language)


@mcp_registry.tool(
    name="cellar_search",
    description="Search EU legal works via official CELLAR SPARQL endpoint.",
    input_schema={
        "type": "object",
        "properties": {
            "query": {"type": "string"},
            "max_results": {"type": "integer", "default": 5},
        },
        "required": ["query"],
    },
)
async def cellar_search(query: str, max_results: int = 5) -> List[Dict[str, Any]]:
    return await cellar.search(query, max_results=int(max_results))


@mcp_registry.tool(
    name="gdpr_article",
    description="Get a GDPR (32016R0679) article excerpt by number.",
    input_schema={
        "type": "object",
        "properties": {"article": {"type": "integer"}},
        "required": ["article"],
    },
)
async def gdpr_article(article: int) -> Dict[str, Any]:
    return await eurlex_client.get_gdpr_article(int(article))


@mcp_registry.tool(
    name="memory_upsert_fact",
    description="Store a durable fact/preference in agent memory.",
    input_schema={
        "type": "object",
        "properties": {
            "key": {"type": "string"},
            "value": {"type": "string"},
        },
        "required": ["key", "value"],
    },
)
async def memory_upsert_fact(key: str, value: str) -> Dict[str, str]:
    memory_store.upsert_fact(key, value, source="mcp_tool", confidence=0.85)
    return {"status": "ok", "key": key}


@mcp_registry.tool(
    name="memory_list_facts",
    description="List durable facts from agent memory.",
    input_schema={"type": "object", "properties": {"limit": {"type": "integer", "default": 20}}},
)
async def memory_list_facts(limit: int = 20) -> List[Dict[str, Any]]:
    return memory_store.get_facts(limit=int(limit))


@mcp_registry.tool(
    name="skills_list",
    description="List distilled agent skills.",
    input_schema={"type": "object", "properties": {}},
)
async def skills_list() -> List[Dict[str, Any]]:
    return skill_manager.list_skills()


@mcp_registry.tool(
    name="echo",
    description="Echo back a message (health/debug).",
    input_schema={
        "type": "object",
        "properties": {"message": {"type": "string"}},
        "required": ["message"],
    },
)
async def echo(message: str) -> Dict[str, str]:
    return {"echo": message}
