"""PostgreSQL memory backend. DATABASE_URL=postgresql://..."""
from __future__ import annotations
import json, logging, time, uuid
from pathlib import Path
from typing import Any, Dict, List, Optional
logger = logging.getLogger("vrav.memory.pg")
SCHEMA = """
CREATE TABLE IF NOT EXISTS sessions (
    id TEXT PRIMARY KEY, created_at DOUBLE PRECISION, updated_at DOUBLE PRECISION,
    title TEXT, meta TEXT);
CREATE TABLE IF NOT EXISTS turns (
    id TEXT PRIMARY KEY, session_id TEXT REFERENCES sessions(id),
    role TEXT, content TEXT, created_at DOUBLE PRECISION);
CREATE TABLE IF NOT EXISTS facts (
    id TEXT PRIMARY KEY, key TEXT UNIQUE, value TEXT, source TEXT,
    confidence DOUBLE PRECISION, created_at DOUBLE PRECISION, updated_at DOUBLE PRECISION);
CREATE INDEX IF NOT EXISTS idx_turns_session ON turns(session_id);
CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key);
"""

class PostgresMemoryStore:
    def __init__(self, database_url: str, md_path: Optional[Path] = None):
        import psycopg
        from psycopg.rows import dict_row
        self.database_url = database_url
        self._psycopg = psycopg
        self._dict_row = dict_row
        root = Path(__file__).resolve().parents[2]
        self.md_path = md_path or (root / "data" / "memory" / "MEMORY.md")
        try:
            self.md_path.parent.mkdir(parents=True, exist_ok=True)
            if not self.md_path.exists():
                self.md_path.write_text("# VRAV MEMORY\n\n", encoding="utf-8")
        except OSError:
            pass
        self._init_db()

    def _conn(self):
        return self._psycopg.connect(self.database_url, row_factory=self._dict_row)

    def _init_db(self) -> None:
        with self._conn() as conn:
            conn.execute(SCHEMA)
            conn.commit()

    def create_session(self, title: str = "", meta: Optional[Dict] = None) -> str:
        sid = str(uuid.uuid4()); now = time.time()
        with self._conn() as conn:
            conn.execute("INSERT INTO sessions (id, created_at, updated_at, title, meta) VALUES (%s,%s,%s,%s,%s)",
                        (sid, now, now, title or "session", json.dumps(meta or {})))
            conn.commit()
        return sid

    def add_turn(self, session_id: str, role: str, content: str) -> str:
        tid = str(uuid.uuid4()); now = time.time()
        with self._conn() as conn:
            conn.execute("INSERT INTO turns (id, session_id, role, content, created_at) VALUES (%s,%s,%s,%s,%s)",
                        (tid, session_id, role, content, now))
            conn.execute("UPDATE sessions SET updated_at=%s WHERE id=%s", (now, session_id))
            conn.commit()
        return tid

    def get_session_turns(self, session_id: str, limit: int = 40) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT role, content, created_at FROM turns WHERE session_id=%s ORDER BY created_at DESC LIMIT %s",
                (session_id, limit)).fetchall()
        return [{"role": r["role"], "content": r["content"], "ts": r["created_at"]} for r in reversed(list(rows))]

    def search_turns(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT session_id, role, content, created_at FROM turns WHERE content ILIKE %s ORDER BY created_at DESC LIMIT %s",
                (f"%{query}%", limit)).fetchall()
        return [dict(r) for r in rows]

    def upsert_fact(self, key: str, value: str, source: str = "agent", confidence: float = 0.8) -> None:
        now = time.time()
        with self._conn() as conn:
            conn.execute("""INSERT INTO facts (id, key, value, source, confidence, created_at, updated_at)
                VALUES (%s,%s,%s,%s,%s,%s,%s)
                ON CONFLICT (key) DO UPDATE SET value=EXCLUDED.value, source=EXCLUDED.source,
                confidence=EXCLUDED.confidence, updated_at=EXCLUDED.updated_at""",
                (str(uuid.uuid4()), key, value, source, confidence, now, now))
            conn.commit()

    def get_facts(self, limit: int = 50) -> List[Dict[str, Any]]:
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT key, value, source, confidence, updated_at FROM facts ORDER BY updated_at DESC LIMIT %s",
                (limit,)).fetchall()
        return [dict(r) for r in rows]

    def get_fact(self, key: str) -> Optional[str]:
        with self._conn() as conn:
            row = conn.execute("SELECT value FROM facts WHERE key=%s", (key,)).fetchone()
        return row["value"] if row else None

    def build_context_block(self, session_id: Optional[str] = None, max_turns: int = 12) -> str:
        parts = []
        facts = self.get_facts(20)
        if facts:
            parts.append("## Known facts / preferences")
            for f in facts:
                parts.append(f"- {f['key']}: {f['value']}")
        if session_id:
            for t in self.get_session_turns(session_id, max_turns):
                parts.append(f"{t['role']}: {t['content'][:500]}")
        return "\n".join(parts) if parts else ""
