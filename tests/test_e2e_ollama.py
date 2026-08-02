"""E2E against live Ollama — auto-skipped when Ollama is down."""
from __future__ import annotations
import os
import httpx
import pytest

OLLAMA = os.environ.get("OLLAMA_BASE_URL", "http://127.0.0.1:11434").rstrip("/")
MODEL = os.environ.get("VRAV_E2E_MODEL", os.environ.get("OLLAMA_DEFAULT_MODEL", "llama3.1"))

def ollama_up() -> bool:
    try:
        return httpx.get(f"{OLLAMA}/api/tags", timeout=2.0).status_code == 200
    except Exception:
        return False

pytestmark = pytest.mark.skipif(not ollama_up(), reason="Ollama not running")

def test_e2e_health_when_ollama_up():
    from fastapi.testclient import TestClient
    from main import app
    assert TestClient(app).get("/api/health").status_code == 200
