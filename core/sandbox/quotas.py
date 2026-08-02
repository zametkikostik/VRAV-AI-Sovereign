"""
Per-user sandbox quotas: runs, CPU time, and code size windows.
Persisted in SQLite so quotas survive restarts.
"""

from __future__ import annotations

import sqlite3
import time
from pathlib import Path
from typing import Any, Dict

from config.settings import settings

DEFAULTS = {
    "max_runs": 30,          # per window
    "max_cpu_ms": 60_000,    # cumulative CPU budget per window
    "max_code_bytes": 32_000,
    "window_sec": 3600,
}


class QuotaManager:
    def __init__(self, db_path: str | None = None):
        base = Path(settings.data_dir if hasattr(settings, "data_dir") else "data")
        base.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or str(base / "quotas.db")
        self._init()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init(self) -> None:
        with self._conn() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS usage (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id TEXT NOT NULL,
                    ts REAL NOT NULL,
                    cpu_ms REAL NOT NULL,
                    code_bytes INTEGER NOT NULL,
                    ok INTEGER NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_usage_user_ts ON usage(user_id, ts)"
            )

    def check(self, user_id: str, code_len: int) -> Dict[str, Any]:
        user_id = (user_id or "default")[:64]
        window = DEFAULTS["window_sec"]
        cutoff = time.time() - window
        with self._conn() as conn:
            rows = conn.execute(
                "SELECT cpu_ms, code_bytes FROM usage WHERE user_id=? AND ts>=?",
                (user_id, cutoff),
            ).fetchall()
        used_runs = len(rows)
        used_cpu = sum(float(r["cpu_ms"]) for r in rows)
        status = {
            "user_id": user_id,
            "used_runs": used_runs,
            "used_cpu_ms": used_cpu,
            "max_runs": DEFAULTS["max_runs"],
            "max_cpu_ms": DEFAULTS["max_cpu_ms"],
            "max_code_bytes": DEFAULTS["max_code_bytes"],
            "window_sec": window,
            "allowed": True,
            "reason": "ok",
        }
        if code_len > DEFAULTS["max_code_bytes"]:
            status["allowed"] = False
            status["reason"] = "code too large"
        elif used_runs >= DEFAULTS["max_runs"]:
            status["allowed"] = False
            status["reason"] = "run quota exceeded"
        elif used_cpu >= DEFAULTS["max_cpu_ms"]:
            status["allowed"] = False
            status["reason"] = "cpu quota exceeded"
        return status

    def record(self, user_id: str, cpu_ms: float, code_bytes: int, ok: bool) -> None:
        user_id = (user_id or "default")[:64]
        with self._conn() as conn:
            conn.execute(
                "INSERT INTO usage (user_id, ts, cpu_ms, code_bytes, ok) VALUES (?,?,?,?,?)",
                (user_id, time.time(), float(cpu_ms), int(code_bytes), 1 if ok else 0),
            )


quota_manager = QuotaManager()
