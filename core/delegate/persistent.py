"""Persistent multi-agent sessions — continue work across HTTP requests."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

from core.delegate.coordinator import MultiAgentDelegate, AGENT_SPECS
from core.sessions.store import session_store
from core.safety.injection import InjectionGuard
from core.safety.policy import policy_gate

logger = logging.getLogger("vrav.persistent")


class PersistentMultiAgent:
    def __init__(self):
        self.delegate = MultiAgentDelegate()

    async def start(self, prompt: str, agents: Optional[List[str]] = None) -> Dict[str, Any]:
        prompt = InjectionGuard.check(prompt)
        ok, reason = policy_gate.check_text(prompt)
        if not ok:
            return {"error": reason}

        planned = agents or self.delegate.plan_agents(prompt)
        sid = session_store.create(title=prompt[:80], agents=planned)
        session_store.add_turn(sid, "user", "user", prompt)
        session_store.update_blackboard(sid, {"plan": planned, "goal": prompt})

        result = await self.delegate.run(prompt, parallel=True)
        session_store.add_turn(sid, "system", "assistant", result.get("final") or "", meta={"trace_agents": result.get("agents_used")})
        for t in result.get("trace") or []:
            session_store.add_turn(
                sid,
                t.get("agent") or "agent",
                "assistant",
                t.get("text") or "",
                meta={"ok": t.get("ok"), "model": t.get("model")},
            )
        session_store.update_blackboard(
            sid,
            {"notes": [f"Completed primary run with agents: {result.get('agents_used')}"], "facts": []},
        )
        return {"session_id": sid, "agents": planned, "result": result, "status": "active"}

    async def continue_session(self, session_id: str, prompt: str) -> Dict[str, Any]:
        prompt = InjectionGuard.check(prompt)
        ok, reason = policy_gate.check_text(prompt)
        if not ok:
            return {"error": reason}

        sess = session_store.get(session_id)
        if not sess:
            return {"error": "session not found"}
        if sess.get("status") == "closed":
            return {"error": "session closed"}

        session_store.add_turn(session_id, "user", "user", prompt)

        turns = session_store.get_turns(session_id, limit=20)
        history = "\n".join(f"[{t['agent']}/{t['role']}]: {t['content'][:500]}" for t in turns[-12:])
        bb = sess.get("blackboard") or {}
        enriched = (
            f"Persistent session goal: {bb.get('goal', '')}\n"
            f"Blackboard: {bb}\n"
            f"Recent history:\n{history}\n\n"
            f"New user message: {prompt}"
        )

        result = await self.delegate.run(enriched, parallel=True)
        session_store.add_turn(
            session_id, "system", "assistant", result.get("final") or "",
            meta={"continued": True, "agents": result.get("agents_used")},
        )
        session_store.update_blackboard(session_id, {"notes": [f"Continue: {prompt[:100]}"]})
        return {
            "session_id": session_id,
            "result": result,
            "blackboard": session_store.get(session_id).get("blackboard"),
            "status": "active",
        }

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        sess = session_store.get(session_id)
        if not sess:
            return None
        sess["turns"] = session_store.get_turns(session_id)
        return sess

    def list(self, limit: int = 20) -> List[Dict[str, Any]]:
        return session_store.list_sessions(limit=limit)

    def close(self, session_id: str) -> None:
        session_store.close(session_id)


persistent_agents = PersistentMultiAgent()
