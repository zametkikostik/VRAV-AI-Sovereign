"""API key + user auth store (SQLite)."""
from __future__ import annotations
import hashlib, secrets, sqlite3, time
from pathlib import Path
from typing import Any, Dict, List, Optional

DB = Path(__file__).resolve().parents[2] / "data" / "auth" / "auth.db"

def _hash_key(raw: str) -> str:
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()

class AuthStore:
    def __init__(self, db_path: Path = DB):
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init()
        self._ensure_admin()

    def _conn(self):
        c = sqlite3.connect(str(self.db_path))
        c.row_factory = sqlite3.Row
        return c

    def _init(self):
        with self._conn() as conn:
            conn.executescript("""
                CREATE TABLE IF NOT EXISTS users (
                    id TEXT PRIMARY KEY, username TEXT UNIQUE NOT NULL,
                    role TEXT NOT NULL DEFAULT 'user', created_at REAL);
                CREATE TABLE IF NOT EXISTS api_keys (
                    id TEXT PRIMARY KEY, user_id TEXT NOT NULL,
                    key_hash TEXT NOT NULL UNIQUE, prefix TEXT NOT NULL,
                    name TEXT, created_at REAL, last_used REAL, revoked INTEGER DEFAULT 0);
            """)

    def _ensure_admin(self):
        with self._conn() as conn:
            if conn.execute("SELECT id FROM users WHERE username='admin'").fetchone():
                return
            uid = secrets.token_hex(8)
            conn.execute("INSERT INTO users (id, username, role, created_at) VALUES (?,?,?,?)",
                         (uid, "admin", "admin", time.time()))
            raw = "vrav_dev_" + secrets.token_urlsafe(24)
            conn.execute(
                "INSERT INTO api_keys (id, user_id, key_hash, prefix, name, created_at, revoked) VALUES (?,?,?,?,?,?,0)",
                (secrets.token_hex(8), uid, _hash_key(raw), raw[:12], "bootstrap", time.time()))
            try:
                (self.db_path.parent / "BOOTSTRAP_KEY.txt").write_text(raw + "\n", encoding="utf-8")
            except OSError:
                pass

    def create_user(self, username: str, role: str = "user") -> str:
        uid = secrets.token_hex(8)
        with self._conn() as conn:
            conn.execute("INSERT INTO users (id, username, role, created_at) VALUES (?,?,?,?)",
                         (uid, username, role, time.time()))
        return uid

    def create_key(self, user_id: str, name: str = "default") -> str:
        raw = "vrav_" + secrets.token_urlsafe(32)
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO api_keys (id, user_id, key_hash, prefix, name, created_at, revoked) VALUES (?,?,?,?,?,?,0)",
                (secrets.token_hex(8), user_id, _hash_key(raw), raw[:12], name, time.time()))
        return raw

    def resolve_key(self, raw: str):
        if not raw: return None
        raw = raw.strip()
        if raw.lower().startswith("bearer "): raw = raw[7:].strip()
        h = _hash_key(raw)
        with self._conn() as conn:
            row = conn.execute("""SELECT k.id as key_id, k.prefix, k.name as key_name,
                u.id as user_id, u.username, u.role FROM api_keys k
                JOIN users u ON u.id=k.user_id WHERE k.key_hash=? AND k.revoked=0""", (h,)).fetchone()
            if not row: return None
            conn.execute("UPDATE api_keys SET last_used=? WHERE id=?", (time.time(), row["key_id"]))
        return dict(row)

    def list_users(self):
        with self._conn() as conn:
            return [dict(r) for r in conn.execute("SELECT id, username, role, created_at FROM users")]

    def list_keys(self, user_id=None):
        with self._conn() as conn:
            if user_id:
                rows = conn.execute("SELECT id, user_id, prefix, name, created_at, last_used, revoked FROM api_keys WHERE user_id=?", (user_id,))
            else:
                rows = conn.execute("SELECT id, user_id, prefix, name, created_at, last_used, revoked FROM api_keys")
            return [dict(r) for r in rows]

    def revoke_key(self, key_id: str):
        with self._conn() as conn:
            conn.execute("UPDATE api_keys SET revoked=1 WHERE id=?", (key_id,))

auth_store = AuthStore()
