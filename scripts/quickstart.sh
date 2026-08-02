#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
echo "== 1. Python deps =="
python -m pip install -q -r requirements.txt
python -m pip install -q pytest pytest-asyncio httpx || true
echo "== 2. Env =="
[[ -f .env ]] || cp .env.example .env
echo "== 3. Ollama models =="
if command -v ollama >/dev/null 2>&1; then
  ollama pull "${OLLAMA_DEFAULT_MODEL:-llama3.1}" || true
  ollama pull "${EMBED_MODEL:-nomic-embed-text}" || true
fi
echo "== 4. Index corpus =="
PYTHONPATH=. python scripts/index_docs.py || true
echo "Ready: uvicorn main:app --reload"
