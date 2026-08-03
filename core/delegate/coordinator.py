"""Multi-agent delegate: roles, LLM planner, parallelism limits, SSE."""
from __future__ import annotations
import asyncio, json, logging, re
from typing import Any, AsyncIterator, Dict, List, Optional
import httpx
from config.settings import settings
from core.mcp.protocol import mcp_registry
from core.rag.skill_index import skill_rag
from core.safety.guard import AntiHallucinationGuard
from core.streaming.sse import sse_event
logger = logging.getLogger("vrav.delegate")
AGENT_SPECS = {
    "legal": {"system": "LEGAL sub-agent EU/BG law. Cite CELEX. No invented articles. Not legal advice.", "model_hint": "bggpt"},
    "research": {"system": "RESEARCH sub-agent. Facts, structure, flag gaps.", "model_hint": "llama3.1"},
    "coding": {"system": "CODING sub-agent. Safe code only. No destructive commands.", "model_hint": "llama3.1"},
    "math": {"system": "MATH sub-agent. Step by step. Verify arithmetic.", "model_hint": "llama3.1"},
    "devops": {"system": "DEVOPS sub-agent. Docker, CI, Linux. Prefer reversible ops.", "model_hint": "llama3.1"},
    "translator": {"system": "TRANSLATOR BG/EN/RU. Preserve technical terms.", "model_hint": "llama3.1"},
    "critic": {"system": "CRITIC. Find hallucinations; output improved final answer.", "model_hint": "llama3.1"},
}
ALL_PRIMARY = ["legal", "research", "coding", "math", "devops", "translator"]
DEFAULT_AGENT_TIMEOUT = float(getattr(settings, "delegate_agent_timeout_sec", 120) or 120)
DEFAULT_MAX_PARALLEL = int(getattr(settings, "delegate_max_parallel", 3) or 3)

class MultiAgentDelegate:
    def __init__(self):
        self.ollama_url = settings.ollama_base_url
        self.guard = AntiHallucinationGuard()
        self.agent_timeout = DEFAULT_AGENT_TIMEOUT
        self.max_parallel = max(1, DEFAULT_MAX_PARALLEL)

    def plan_agents(self, prompt: str) -> List[str]:
        lower = prompt.lower(); agents = []
        if any(k in lower for k in ("закон", "gdpr", "celex", "регламент", "legal", "право")): agents.append("legal")
        if any(k in lower for k in ("код", "code", "python", "debug", "api", "script")): agents.append("coding")
        if any(k in lower for k in ("math", "equation", "уравнен", "calculate", "изчисл")): agents.append("math")
        if any(k in lower for k in ("docker", "nginx", "devops", "deploy", "k8s")): agents.append("devops")
        if any(k in lower for k in ("translate", "превод", "преведи", "to english")): agents.append("translator")
        if not agents: agents.append("research")
        agents.append("critic"); return agents

    async def plan_agents_llm(self, prompt: str) -> List[str]:
        if not getattr(settings, "delegate_llm_planner", True):
            return self.plan_agents(prompt)
        try:
            text = await self._call_ollama([
                {"role": "system", "content": f"Pick 1-3 of {ALL_PRIMARY} then critic. JSON only: {{\"agents\":[...]}}"},
                {"role": "user", "content": prompt[:2000]},
            ], model=settings.ollama_default_model, temperature=0.1, timeout=30.0)
            m = re.search(r"\{[\s\S]*\}", text)
            if not m: return self.plan_agents(prompt)
            chosen = [a for a in json.loads(m.group(0)).get("agents", []) if a in AGENT_SPECS]
            if not chosen: return self.plan_agents(prompt)
            primary = [a for a in chosen if a != "critic"][:3]
            return primary + ["critic"]
        except Exception:
            return self.plan_agents(prompt)

    async def _call_ollama(self, messages, model, temperature=0.4, timeout=None):
        to = timeout if timeout is not None else self.agent_timeout
        async with httpx.AsyncClient(timeout=to) as client:
            resp = await client.post(f"{self.ollama_url.rstrip('/')}/api/chat",
                json={"model": model, "messages": messages, "stream": False, "options": {"temperature": temperature}})
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    async def _retrieve_skills(self, prompt):
        hits = await skill_rag.retrieve(prompt, top_k=4, min_score=0.28)
        return skill_rag.format_for_prompt(hits), hits

    async def _run_agent(self, name, prompt, context="", skill_block="", prior=None):
        spec = AGENT_SPECS[name]
        model = settings.bggpt_model if spec["model_hint"] == "bggpt" else settings.ollama_default_model
        if name == "coding" and getattr(settings, "ollama_coder_model", None):
            model = settings.ollama_coder_model
        system = spec["system"]
        if skill_block: system += "\n\n" + skill_block
        if context: system += "\n\n## Context\n" + context[:6000]
        if prior:
            system += "\n\n## Prior\n" + "".join(f"\n### {k}\n{v[:2000]}\n" for k, v in prior.items())
        try:
            text = await asyncio.wait_for(self._call_ollama([
                {"role": "system", "content": system}, {"role": "user", "content": prompt}
            ], model=model), timeout=self.agent_timeout + 5)
            return {"agent": name, "ok": True, "text": text, "model": model}
        except asyncio.TimeoutError:
            return {"agent": name, "ok": False, "text": f"[timeout {name}]", "model": model}
        except Exception as e:
            return {"agent": name, "ok": False, "text": f"[error {name}: {e}]", "model": model}

    async def _gather_tools(self, prompt):
        parts = []
        try:
            if any(k in prompt.lower() for k in ("gdpr", "eur-lex", "celex", "регламент")):
                r = await mcp_registry.call_tool("cellar_search", {"query": prompt[:100], "max_results": 3})
                parts.append(str(r)[:2000])
        except Exception as e:
            parts.append(str(e))
        return "\n\n".join(parts)

    async def run(self, prompt, parallel=True, agents=None, use_llm_planner=True):
        planned = agents if agents else (await self.plan_agents_llm(prompt) if use_llm_planner else self.plan_agents(prompt))
        planned = [a for a in planned if a in AGENT_SPECS]
        if "critic" not in planned: planned.append("critic")
        tool_ctx = await self._gather_tools(prompt)
        skill_block, skill_hits = await self._retrieve_skills(prompt)
        primary = [a for a in planned if a != "critic"]
        results, trace = {}, []
        if parallel and len(primary) > 1:
            for i in range(0, len(primary), self.max_parallel):
                batch = primary[i:i+self.max_parallel]
                for out in await asyncio.gather(*[self._run_agent(a, prompt, tool_ctx, skill_block) for a in batch]):
                    results[out["agent"]] = out["text"]; trace.append(out)
        else:
            for a in primary:
                out = await self._run_agent(a, prompt, tool_ctx, skill_block, results)
                results[a] = out["text"]; trace.append(out)
        final = results.get(primary[-1], "") if primary else ""
        if "critic" in planned:
            out = await self._run_agent("critic", prompt, tool_ctx, skill_block, results)
            results["critic"] = out["text"]; trace.append(out); final = out["text"]
        validated = await self.guard.validate_response(final, {"prompt": prompt, "tool_context": tool_ctx,
            "grounding_docs": [h.get("content") or "" for h in skill_hits] + ([tool_ctx] if tool_ctx else [])})
        return {"agents_used": planned, "trace": trace, "final": validated["response"],
                "confidence": validated.get("confidence"), "grounding_score": validated.get("grounding_score"),
                "skills_retrieved": [{"name": h["name"], "score": h["score"]} for h in skill_hits],
                "max_parallel": self.max_parallel, "agent_timeout_sec": self.agent_timeout}

    async def run_stream(self, prompt, parallel=True, agents=None, use_llm_planner=True):
        yield sse_event("status", {"phase": "delegate"})
        planned = agents if agents else (await self.plan_agents_llm(prompt) if use_llm_planner else self.plan_agents(prompt))
        planned = [a for a in planned if a in AGENT_SPECS]
        if "critic" not in planned: planned.append("critic")
        yield sse_event("plan", {"agents": planned})
        tool_ctx = await self._gather_tools(prompt)
        skill_block, skill_hits = await self._retrieve_skills(prompt)
        primary = [a for a in planned if a != "critic"]; results, trace = {}, []
        async def one(name, prior=None):
            return await self._run_agent(name, prompt, tool_ctx, skill_block, prior)
        if parallel and len(primary) > 1:
            for i in range(0, len(primary), self.max_parallel):
                batch = primary[i:i+self.max_parallel]
                for a in batch: yield sse_event("agent_start", {"agent": a})
                for out in await asyncio.gather(*[one(a) for a in batch]):
                    results[out["agent"]] = out["text"]; trace.append(out)
                    yield sse_event("agent_done", {"agent": out["agent"], "ok": out["ok"], "preview": out["text"][:500]})
        else:
            for a in primary:
                yield sse_event("agent_start", {"agent": a})
                out = await one(a, results)
                results[a] = out["text"]; trace.append(out)
                yield sse_event("agent_done", {"agent": a, "ok": out["ok"], "preview": out["text"][:500]})
        final = results.get(primary[-1], "") if primary else ""
        if "critic" in planned:
            yield sse_event("agent_start", {"agent": "critic"})
            out = await one("critic", results)
            final = out["text"]
            yield sse_event("agent_done", {"agent": "critic", "ok": out["ok"], "preview": out["text"][:500]})
        validated = await self.guard.validate_response(final, {"prompt": prompt, "grounding_docs": []})
        ft = validated["response"]
        for i in range(0, len(ft), 48):
            yield sse_event("token", {"text": ft[i:i+48]})
        yield sse_event("done", {"agents_used": planned, "confidence": validated.get("confidence"),
                                  "grounding_score": validated.get("grounding_score"), "length": len(ft)})

delegate = MultiAgentDelegate()
