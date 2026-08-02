"""Background skill-review agent (Hermes-style)."""

from __future__ import annotations

import asyncio
import logging
import re
from typing import Any, Dict, List, Optional

from core.memory.store import memory_store
from core.skills.manager import skill_manager

logger = logging.getLogger("vrav.skill_review")

_USEFUL_SIGNALS = (
    r"закон", r"регламент", r"директива", r"gdpr", r"celex",
    r"процедур", r"how to", r"стъпк", r"workflow", r"review", r"deploy", r"debug",
)


class SkillReviewer:
    def __init__(self):
        self._queue: asyncio.Queue = asyncio.Queue()
        self._worker_started = False

    def start_worker(self) -> None:
        if self._worker_started:
            return
        try:
            loop = asyncio.get_running_loop()
            loop.create_task(self._worker())
            self._worker_started = True
        except RuntimeError:
            pass

    def enqueue(self, session_id: str, prompt: str, response: str, meta: Optional[Dict] = None) -> None:
        self.start_worker()
        try:
            self._queue.put_nowait({
                "session_id": session_id, "prompt": prompt,
                "response": response, "meta": meta or {},
            })
        except asyncio.QueueFull:
            logger.warning("Skill review queue full")

    async def _worker(self) -> None:
        while True:
            job = await self._queue.get()
            try:
                await self.review_session(**job)
            except Exception as e:
                logger.exception("Skill review failed: %s", e)
            finally:
                self._queue.task_done()

    async def review_session(
        self, session_id: str, prompt: str, response: str, meta: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        meta = meta or {}
        use_llm = meta.get("use_llm", True)
        if use_llm:
            try:
                from core.skills.llm_reviewer import llm_skill_reviewer
                return await llm_skill_reviewer.review_session(session_id, prompt, response, meta)
            except Exception as e:
                logger.warning("LLM reviewer path failed: %s", e)
        result: Dict[str, Any] = {"session_id": session_id, "actions": [], "mode": "heuristic"}
        facts = self._extract_facts(prompt, response)
        for key, value in facts.items():
            memory_store.upsert_fact(key, value, source="skill_review", confidence=0.7)
            result["actions"].append({"type": "fact", "key": key, "value": value})
        if not self._is_skill_worthy(prompt, response):
            result["actions"].append({"type": "skip", "reason": "not skill-worthy"})
            return result
        steps = self._infer_steps(prompt, response, meta)
        name = skill_manager.record_success(
            task_pattern=prompt[:120], steps=steps, outcome=response[:240], tags=self._tags(prompt),
        )
        if name:
            result["actions"].append({"type": "skill_created", "name": name})
        return result

    def _is_skill_worthy(self, prompt: str, response: str) -> bool:
        if len(prompt) < 20 or len(response) < 40:
            return False
        text = (prompt + " " + response).lower()
        return any(re.search(p, text) for p in _USEFUL_SIGNALS)

    def _infer_steps(self, prompt: str, response: str, meta: Optional[Dict]) -> List[str]:
        steps = re.findall(r"(?:^|\n)\s*(?:\d+[.)]|[-*])\s+(.+)", response)
        steps = [s.strip()[:120] for s in steps if len(s.strip()) > 3][:12]
        if not steps:
            steps = ["Analyze request", "Use tools if needed", "Answer with confidence"]
        return steps

    def _tags(self, prompt: str) -> List[str]:
        tags = []
        lower = prompt.lower()
        if any(k in lower for k in ("gdpr", "закон", "legal", "celex")):
            tags.append("legal")
        if any(k in lower for k in ("code", "python", "api")):
            tags.append("coding")
        return tags or ["general"]

    def _extract_facts(self, prompt: str, response: str) -> Dict[str, str]:
        facts = {}
        m = re.search(r"(?:предпочитам|prefer|language|език)[:\s]+([a-zа-я]{2,10})", prompt, re.I)
        if m:
            facts["user.language"] = m.group(1).lower()
        return facts


skill_reviewer = SkillReviewer()
