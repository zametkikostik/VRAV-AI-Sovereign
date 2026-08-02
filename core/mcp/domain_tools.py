"""Domain MCP tools: BG/EU legal + calc + datetime + doc RAG."""
from __future__ import annotations
import ast, operator, re
from datetime import datetime, timezone
from typing import Any, Dict
from zoneinfo import ZoneInfo
from core.mcp.protocol import mcp_registry

_OPS = {
    ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
    ast.Div: operator.truediv, ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod, ast.Pow: operator.pow, ast.USub: operator.neg,
}

def _eval_node(node):
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return float(node.value)
    if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.left), _eval_node(node.right))
    if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
        return _OPS[type(node.op)](_eval_node(node.operand))
    raise ValueError("Only basic arithmetic allowed")

@mcp_registry.tool(name="calc", description="Safe arithmetic calculator.",
    input_schema={"type": "object", "properties": {"expression": {"type": "string"}}, "required": ["expression"]})
async def calc(expression: str) -> Dict[str, Any]:
    expr = (expression or "").strip()
    if len(expr) > 200 or not re.match(r"^[\d\s\.\+\-\*/%()]+$", expr):
        return {"error": "invalid expression"}
    try:
        return {"expression": expr, "result": _eval_node(ast.parse(expr, mode="eval").body)}
    except Exception as e:
        return {"error": str(e)}

@mcp_registry.tool(name="datetime_now", description="UTC and Europe/Sofia time.",
    input_schema={"type": "object", "properties": {}})
async def datetime_now() -> Dict[str, str]:
    utc = datetime.now(timezone.utc)
    sofia = utc.astimezone(ZoneInfo("Europe/Sofia"))
    return {"utc": utc.isoformat(), "sofia": sofia.isoformat(),
            "sofia_date": sofia.strftime("%Y-%m-%d"),
            "weekday_bg": ["понеделник","вторник","сряда","четвъртък","петък","събота","неделя"][sofia.weekday()]}

_LEGAL_SHORTCUTS = {"gdpr": "32016R0679", "eidas": "32014R0910", "dsa": "32022R2065",
                    "dma": "32022R1925", "aia": "32024R1689", "nis2": "32022L2555"}

@mcp_registry.tool(name="bg_legal_lookup", description="Resolve legal short name to CELEX and fetch text.",
    input_schema={"type": "object", "properties": {"name_or_celex": {"type": "string"}, "language": {"type": "string", "default": "bg"}}, "required": ["name_or_celex"]})
async def bg_legal_lookup(name_or_celex: str, language: str = "bg") -> Dict[str, Any]:
    from core.tools.eurlex import eurlex_client
    from core.tools.cellar_sparql import cellar
    key = (name_or_celex or "").strip().lower()
    celex = _LEGAL_SHORTCUTS.get(key) or name_or_celex.strip().upper()
    meta = await cellar.by_celex(celex)
    doc = await eurlex_client.get_by_celex(celex, language=language)
    return {"resolved_celex": celex, "shortcut": key if key in _LEGAL_SHORTCUTS else None,
            "cellar": meta, "document": {"title": doc.get("title"), "url": doc.get("url"),
            "text_preview": (doc.get("text") or "")[:8000], "error": doc.get("error")}}

@mcp_registry.tool(name="bg_labor_code_hint", description="Bulgarian Labor Code topic hints.",
    input_schema={"type": "object", "properties": {"topic": {"type": "string"}}, "required": ["topic"]})
async def bg_labor_code_hint(topic: str) -> Dict[str, Any]:
    topic_l = (topic or "").lower()
    map_ = {
        "dismissal": {"bg": "прекратяване", "hints": ["Основание", "Предизвестие", "Обезщетение"]},
        "leave": {"bg": "отпуск", "hints": ["20 работни дни минимум"]},
        "contract": {"bg": "трудов договор", "hints": ["Реквизити", "Пробен срок"]},
        "working_time": {"bg": "работно време", "hints": ["Извънреден труд ограничен"]},
        "salary": {"bg": "възнаграждение", "hints": ["Минимална заплата", "Срокове"]},
    }
    hit = next((v for k, v in map_.items() if k in topic_l or v["bg"] in topic_l), None)
    if not hit:
        hit = {"bg": topic, "hints": ["Уточни темата"]}
    return {"topic": topic, "guidance": hit, "disclaimer": "Не е юридическа консултация."}

@mcp_registry.tool(name="eu_ai_act_overview", description="EU AI Act risk tiers overview.",
    input_schema={"type": "object", "properties": {}})
async def eu_ai_act_overview() -> Dict[str, Any]:
    return {"celex": "32024R1689", "risk_tiers": [
        {"tier": "unacceptable", "examples": "social scoring"},
        {"tier": "high-risk", "examples": "biometrics, employment, credit"},
        {"tier": "limited risk", "examples": "chatbots — transparency"},
        {"tier": "minimal risk", "examples": "most other systems"},
    ]}

@mcp_registry.tool(name="doc_search", description="Search indexed user documents (data/corpus).",
    input_schema={"type": "object", "properties": {"query": {"type": "string"}, "top_k": {"type": "integer", "default": 5}}, "required": ["query"]})
async def doc_search(query: str, top_k: int = 5) -> Dict[str, Any]:
    from core.rag.doc_index import doc_rag
    hits = await doc_rag.retrieve(query, top_k=int(top_k or 5))
    return {"query": query, "hits": hits, "indexed_chunks": len(doc_rag._chunks)}

@mcp_registry.tool(name="doc_reindex", description="Rebuild document RAG index from data/corpus.",
    input_schema={"type": "object", "properties": {}})
async def doc_reindex() -> Dict[str, Any]:
    from core.rag.doc_index import doc_rag
    return await doc_rag.reindex()
