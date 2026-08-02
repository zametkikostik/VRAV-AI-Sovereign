#!/usr/bin/env bash
set -euo pipefail
BASE="${VRAV_BASE:-http://127.0.0.1:8000}"
echo "== health =="
curl -sf "$BASE/api/health" | head -c 400; echo
echo "== mcp tools =="
curl -sf "$BASE/api/mcp/tools" | head -c 600; echo
echo "== sandbox =="
curl -sf -X POST "$BASE/api/sandbox/run" -H 'Content-Type: application/json' -d '{"code":"print(2+2)"}' | head -c 400; echo
echo "== smoke ok =="
