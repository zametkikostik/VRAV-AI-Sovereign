"""LLM-powered skill reviewer with heuristic fallback."""

from __future__ import annotations

import json
import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from core.memory.store import memory_store
from core.skills.manager import skill_manager
from core.skills.reviewer import SkillReviewer

logger = logging.getLogger("vrav.llm_review")

REVIEW_SYSTEM = """You are the VRAV skill-review agent.
Analyze the user prompt and assistant response. Reply with ONLY valid JSON:
{
  "actions": [
    {"type": "create_skill", "name": "snake_case_name", "description": "...", "steps": ["..."], "tags": ["..."]},
    {"type": "refine_skill", "name": "existing_or_new", "note": "..."},
    {"type": "upsert_fact", "key": "user.pref.x", "value": "..."},
    {"type": "skip", "reason": "..."}
  ],
  "summary": "one sentence"
}
Rules: Prefer skip for trivial greetings. create_skill only for reusable workflows.
"""


class LLMSkillReviewer:
    def __init__(self, model: Optional[str] = None):
        self.model = model or settings.ollama_default_model
        self.fallback = SkillReviewer()

    async def review_session(
        self, session_id: str, prompt: str, response: str, meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta = meta or {}
        try:
            raw = await self._call_review_llm(prompt, response, meta)
            parsed = self._parse_json(raw)
            if not parsed:
                return await self.fallback.review_session(session_id, prompt, response, meta)
            applied = await self._apply_actions(parsed.get("actions") or [], session_id, prompt, response)
            return {"session_id": session_id, "mode": "llm", "summary": parsed.get("summary"), "actions": applied}
        except Exception as e:
            logger.warning("LLM review failed (%s) — fallback", e)
            out = await self.fallback.review_session(session_id, prompt, response, meta)
            out["mode"] = "heuristic_fallback"
            return out

    async def _call_review_llm(self, prompt: str, response: str, meta: Dict) -> str:
        user = (
            f"SESSION META: {json.dumps(meta, ensure_ascii=False)}\n\n"
            f"USER PROMPT:\n{prompt[:2000]}\n\nASSISTANT RESPONSE:\n{response[:3000]}"
        )
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{settings.ollama_base_url}/api/chat",
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": REVIEW_SYSTEM},
                        {"role": "user", "content": user},
                    ],
                    "stream": False, "options": {"temperature": 0.1},
                },
            )
            resp.raise_for_status()
            return resp.json()["message"]["content"]

    def _parse_json(self, raw: str) -> Optional[Dict]:
        raw = raw.strip()
        m = re.search(r"\{[\s\S]*\}", raw)
        if not m:
            return None
        try:
            return json.loads(m.group(0))
        except json.JSONDecodeError:
            return None

    async def _apply_actions(self, actions: List[Dict], session_id: str, prompt: str, response: str) -> List[Dict]:
        applied = []
        for a in actions:
            t = a.get("type")
            if t == "create_skill":
                name = skill_manager.record_success(
                    task_pattern=a.get("description") or prompt[:120],
                    steps=a.get("steps") or ["Analyze", "Act", "Verify"],
                    outcome=response[:240], tags=a.get("tags") or [],
                )
                applied.append({"type": "skill_created", "name": name or a.get("name")})
            elif t == "refine_skill" and a.get("name"):
                if skill_manager.refine_skill(a["name"], a.get("note") or f"session {session_id}"):
                    applied.append({"type": "skill_refined", "name": a["name"]})
            elif t == "upsert_fact" and a.get("key"):
                memory_store.upsert_fact(a["key"], str(a.get("value") or ""), source="llm_review")
                applied.append({"type": "fact", "key": a["key"]})
            elif t == "skip":
                applied.append({"type": "skip", "reason": a.get("reason")})
        return applied


llm_skill_reviewer = LLMSkillReviewer()
