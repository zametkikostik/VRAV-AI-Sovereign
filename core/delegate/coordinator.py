"""Multi-agent delegate coordinator + hard skill RAG filtering."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from core.mcp.protocol import mcp_registry
from core.rag.skill_index import skill_rag
from core.safety.guard import AntiHallucinationGuard

logger = logging.getLogger("vrav.delegate")

AGENT_SPECS: Dict[str, Dict[str, str]] = {
    "legal": {
        "system": (
            "You are the LEGAL sub-agent of VRAV. Focus on EU/Bulgarian law. "
            "Use provided tool results and RAG skills only when relevant. "
            "Cite CELEX when possible. State uncertainty. Do not invent articles."
        ),
        "model_hint": "bggpt",
    },
    "research": {
        "system": (
            "You are the RESEARCH sub-agent of VRAV. Gather facts, structure findings, "
            "avoid speculation. Prefer tool evidence and retrieved skills. Flag gaps."
        ),
        "model_hint": "llama3.1",
    },
    "coding": {
        "system": (
            "You are the CODING sub-agent of VRAV. Provide correct, safe code. "
            "Never suggest destructive commands (rm -rf, eval on untrusted input, etc.). "
            "Prefer sandbox-safe patterns."
        ),
        "model_hint": "llama3.1",
    },
    "critic": {
        "system": (
            "You are the CRITIC sub-agent of VRAV. Review the draft for hallucinations, "
            "missing sources, legal overconfidence. Output: (1) issues (2) improved final answer. "
            "If claims are ungrounded in provided context, lower confidence explicitly."
        ),
        "model_hint": "llama3.1",
    },
}


class MultiAgentDelegate:
    def __init__(self):
        self.ollama_url = settings.ollama_base_url
        self.guard = AntiHallucinationGuard()

    def plan_agents(self, prompt: str) -> List[str]:
        lower = prompt.lower()
        agents: List[str] = []
        if any(k in lower for k in ("закон", "gdpr", "celex", "регламент", "директива", "eu law", "legal")):
            agents.append("legal")
        if any(k in lower for k in ("код", "code", "python", "debug", "function", "api", "script")):
            agents.append("coding")
        if not agents:
            agents.append("research")
        if len(agents) >= 1:
            agents.append("critic")
        return agents

    async def _call_ollama(self, messages: List[Dict[str, str]], model: str, temperature: float = 0.4) -> str:
        async with httpx.AsyncClient(timeout=180.0) as client:
            resp = await client.post(
                f"{self.ollama_url}/api/chat",
                json={"model": model, "messages": messages, "stream": False,
                      "options": {"temperature": temperature}},
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def _retrieve_skills(self, prompt: str):
        hits = await skill_rag.retrieve(prompt, top_k=4, min_score=0.28)
        return skill_rag.format_for_prompt(hits), hits

    async def _run_agent(
        self, name: str, prompt: str, context: str = "", skill_block: str = "",
        prior: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        spec = AGENT_SPECS[name]
        model = settings.bggpt_model if spec["model_hint"] == "bggpt" else settings.ollama_default_model
        system = spec["system"]
        if skill_block:
            system += "\n\n" + skill_block
        if context:
            system += "\n\n## Context / tool results\n" + context[:6000]
        if prior:
            system += "\n\n## Prior sub-agent outputs\n"
            for k, v in prior.items():
                system += f"\n### {k}\n{v[:2000]}\n"
        messages = [{"role": "system", "content": system}, {"role": "user", "content": prompt}]
        try:
            text = await self._call_ollama(messages, model=model)
            return {"agent": name, "ok": True, "text": text, "model": model}
        except Exception as e:
            logger.warning("Sub-agent %s failed: %s", name, e)
            return {"agent": name, "ok": False, "text": f"[agent {name} error: {e}]", "model": model}

    async def _gather_tools(self, prompt: str) -> str:
        parts: List[str] = []
        celex_m = re.search(r"\b([0-9]{5}[A-Za-z][0-9]{4})\b", prompt)
        try:
            if celex_m:
                r = await mcp_registry.call_tool("eurlex_get", {"celex": celex_m.group(1), "language": "en"})
                parts.append(str(r)[:4000])
            if re.search(r"(?i)gdpr.*(?:article|член)\s*(\d+)", prompt):
                m = re.search(r"(?i)(?:article|член)\s*(\d+)", prompt)
                if m:
                    r = await mcp_registry.call_tool("gdpr_article", {"article": int(m.group(1))})
                    parts.append(str(r)[:3000])
            if any(k in prompt.lower() for k in ("eur-lex", "регламент", "directive", "cellar")):
                r = await mcp_registry.call_tool("cellar_search", {"query": prompt[:100], "max_results": 3})
                parts.append(str(r)[:2000])
        except Exception as e:
            parts.append(f"[tool error: {e}]")
        return "\n\n".join(parts)

    async def run(self, prompt: str, parallel: bool = True) -> Dict[str, Any]:
        agents = self.plan_agents(prompt)
        tool_ctx = await self._gather_tools(prompt)
        skill_block, skill_hits = await self._retrieve_skills(prompt)
        results: Dict[str, str] = {}
        trace: List[Dict[str, Any]] = []
        primary = [a for a in agents if a != "critic"]
        critic = "critic" in agents

        if parallel and len(primary) > 1:
            outs = await asyncio.gather(*[
                self._run_agent(a, prompt, context=tool_ctx, skill_block=skill_block) for a in primary
            ])
            for out in outs:
                results[out["agent"]] = out["text"]
                trace.append(out)
        else:
            for a in primary:
                out = await self._run_agent(a, prompt, context=tool_ctx, skill_block=skill_block, prior=results)
                results[a] = out["text"]
                trace.append(out)

        final = results.get(primary[-1], "") if primary else ""
        if critic:
            out = await self._run_agent("critic", prompt, context=tool_ctx, skill_block=skill_block, prior=results)
            results["critic"] = out["text"]
            trace.append(out)
            final = out["text"]

        grounding_docs = [h.get("content") or h.get("description") or "" for h in skill_hits]
        if tool_ctx:
            grounding_docs.append(tool_ctx)
        validated = await self.guard.validate_response(
            final, {"prompt": prompt, "tool_context": tool_ctx, "grounding_docs": grounding_docs},
        )
        return {
            "agents_used": agents,
            "trace": trace,
            "final": validated["response"],
            "confidence": validated.get("confidence"),
            "grounding_score": validated.get("grounding_score"),
            "fact_check": validated.get("fact_check").model_dump()
            if validated.get("fact_check") and hasattr(validated.get("fact_check"), "model_dump")
            else None,
            "skills_retrieved": [{"name": h["name"], "score": h["score"]} for h in skill_hits],
            "tool_context_used": bool(tool_ctx),
        }


delegate = MultiAgentDelegate()
