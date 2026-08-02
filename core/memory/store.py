"""VRAV Memory Layer — episodic sessions + semantic facts."""

from __future__ import annotations

import json
import sqlite3
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data"
MEMORY_DB = DATA_DIR / "memory" / "vrav_memory.db"
MEMORY_MD = DATA_DIR / "memory" / "MEMORY.md"


class MemoryStore:
    def __init__(self, db_path: Path = MEMORY_DB, md_path: Path = MEMORY_MD):
        self.db_path = db_path
        self.md_path = md_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self.md_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()
        if not self.md_path.exists():
            self.md_path.write_text(
                "# VRAV MEMORY\n\n## User preferences\n\n## Durable facts\n\n## Project notes\n",
                encoding="utf-8",
            )

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, created_at REAL, updated_at REAL, title TEXT, meta TEXT);
                CREATE TABLE IF NOT EXISTS turns (
                    id TEXT PRIMARY KEY, session_id TEXT, role TEXT, content TEXT, created_at REAL,
                    FOREIGN KEY(session_id) REFERENCES sessions(id));
                CREATE TABLE IF NOT EXISTS facts (
                    id TEXT PRIMARY KEY, key TEXT UNIQUE, value TEXT, source TEXT,
                    confidence REAL, created_at REAL, updated_at REAL);
                CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
                CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key);
                """
            )

    def create_session(self, title: str = "", meta: Optional[Dict] = None) -> str:
        sid = str(uuid.uuid4())
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO sessions (id, created_at, updated_at, title, meta) VALUES (?,?,?,?,?)",
                (sid, now, now, title or "session", json.dumps(meta or {})),
            )
        return sid

    def add_turn(self, session_id: str, role: str, content: str) -> str:
        tid = str(uuid.uuid4())
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO turns (id, session_id, role, content, created_at) VALUES (?,?,?,?,?)",
                (tid, session_id, role, content, now),
            )
            conn.execute("UPDATE sessions SET updated_at=? WHERE id=?", (now, session_id))
        return tid

    def get_session_turns(self, session_id: str, limit: int = 40) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM turns WHERE session_id=? ORDER BY created_at DESC LIMIT ?",
                (session_id, limit),
            ).fetchall()
        return [{"role": r["role"], "content": r["content"], "ts": r["created_at"]} for r in reversed(rows)]

    def search_turns(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        q = f"%{query}%"
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT session_id, role, content, created_at FROM turns WHERE content LIKE ? ORDER BY created_at DESC LIMIT ?",
                (q, limit),
            ).fetchall()
        return [dict(r) for r in rows]

    def upsert_fact(self, key: str, value: str, source: str = "agent", confidence: float = 0.8) -> None:
        now = time.time()
        with self._conn() as conn:
            conn.execute(
                """INSERT INTO facts (id, key, value, source, confidence, created_at, updated_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value=excluded.value, source=excluded.source,
                    confidence=excluded.confidence, updated_at=excluded.updated_at""",
                (str(uuid.uuid4()), key, value, source, confidence, now, now),
            )
        self._append_memory_md(key, value)

    def get_facts(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key, value, source, confidence, updated_at FROM facts ORDER BY updated_at DESC LIMIT ?",
                (limit,),
            ).fetchall()
        return [dict(r) for r in rows]

    def get_fact(self, key: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM facts WHERE key=?", (key,)).fetchone()
        return row["value"] if row else None

    def build_context_block(self, session_id: Optional[str] = None, max_turns: int = 12) -> str:
        parts: List[str] = []
        facts = self.get_facts(limit=20)
        if facts:
            parts.append("## Known facts / preferences")
            for f in facts:
                parts.append(f"- {f['key']}: {f['value']}")
        md = self.md_path.read_text(encoding="utf-8") if self.md_path.exists() else ""
        if md.strip():
            snippet = "\n".join(md.strip().splitlines()[:40])
            parts.append("## MEMORY.md excerpt\n" + snippet)
        if session_id:
            turns = self.get_session_turns(session_id, limit=max_turns)
            if turns:
                parts.append("## Recent conversation")
                for t in turns:
                    parts.append(f"{t['role']}: {t['content'][:500]}")
        return "\n".join(parts) if parts else ""

    def _append_memory_md(self, key: str, value: str) -> None:
        line = f"- **{key}**: {value}\n"
        existing = self.md_path.read_text(encoding="utf-8") if self.md_path.exists() else ""
        if key in existing:
            return
        with open(self.md_path, "a", encoding="utf-8") as f:
            f.write(line)


_memory_store = None

def get_memory_store() -> MemoryStore:
    global _memory_store
    if _memory_store is None:
        _memory_store = MemoryStore()
    return _memory_store

class _LazyProxy:
    def __getattr__(self, name):
        return getattr(get_memory_store(), name)

memory_store = _LazyProxy()
