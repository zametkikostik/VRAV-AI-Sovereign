"""Persistent multi-agent sessions."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "sessions"
DB_PATH = DATA_DIR / "multi_agent.db"


class SessionStore:
    def __init__(self, db_path: Path = DB_PATH):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS agent_sessions (
                    id TEXT PRIMARY KEY,
                    created_at REAL,
                    updated_at REAL,
                    title TEXT,
                    agents TEXT,
                    blackboard TEXT,
                    status TEXT
                );
                CREATE TABLE IF NOT EXISTS agent_turns (
                    id TEXT PRIMARY KEY,
                    session_id TEXT,
                    agent TEXT,
                    role TEXT,
                    content TEXT,
                    meta TEXT,
                    created_at REAL,
                    FOREIGN KEY(session_id) REFERENCES agent_sessions(id)
                );
                CREATE INDEX IF NOT EXISTS idx_at_session ON agent_turns(session_id);
                """
            )

    def create(self, title: str = "", agents: Optional[List[str]] = None) -> str:
        sid = str(uuid.uuid4())
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO agent_sessions (id, created_at, updated_at, title, agents, blackboard, status) VALUES (?,?,?,?,?,?,?)",
                (sid, now, now, title[:120] or "multi-agent",
                 json.dumps(agents or ["legal", "research", "critic"]),
                 json.dumps({"notes": [], "facts": [], "plan": []}), "active"),
            )
        return sid

    def get(self, session_id: str) -> Optional[Dict[str, Any]]:
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM agent_sessions WHERE id=?", (session_id,)).fetchone()
        if not row:
            return None
        return {
            "id": row["id"], "title": row["title"],
            "agents": json.loads(row["agents"] or "[]"),
            "blackboard": json.loads(row["blackboard"] or "{}"),
            "status": row["status"], "created_at": row["created_at"], "updated_at": row["updated_at"],
        }

    def update_blackboard(self, session_id: str, patch: Dict[str, Any]) -> None:
        sess = self.get(session_id)
        if not sess:
            return
        bb = sess["blackboard"]
        for k, v in patch.items():
            if isinstance(v, list) and isinstance(bb.get(k), list):
                bb[k] = (bb.get(k) or []) + v
            else:
                bb[k] = v
        with self._conn() as conn:
            conn.execute("UPDATE agent_sessions SET blackboard=?, updated_at=? WHERE id=?",
                         (json.dumps(bb), time.time(), session_id))

    def add_turn(self, session_id: str, agent: str, role: str, content: str, meta: Optional[Dict] = None) -> str:
        tid = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO agent_turns (id, session_id, agent, role, content, meta, created_at) VALUES (?,?,?,?,?,?,?)",
                (tid, session_id, agent, role, content, json.dumps(meta or {}), time.time()),
            )
            conn.execute("UPDATE agent_sessions SET updated_at=? WHERE id=?", (time.time(), session_id))
        return tid

    def get_turns(self, session_id: str, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT agent, role, content, meta, created_at FROM agent_turns WHERE session_id=? ORDER BY created_at ASC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [{"agent": r["agent"], "role": r["role"], "content": r["content"],
                 "meta": json.loads(r["meta"] or "{}"), "ts": r["created_at"]} for r in rows]

    def list_sessions(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT id, title, status, updated_at, agents FROM agent_sessions ORDER BY updated_at DESC LIMIT ?", (limit,)
            ).fetchall()
        return [{"id": r["id"], "title": r["title"], "status": r["status"],
                 "updated_at": r["updated_at"], "agents": json.loads(r["agents"] or "[]")} for r in rows]

    def close(self, session_id: str) -> None:
        with self._conn() as conn:
            conn.execute("UPDATE agent_sessions SET status=?, updated_at=? WHERE id=?",
                         ("closed", time.time(), session_id))


session_store = SessionStore()
