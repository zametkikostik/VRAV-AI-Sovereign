#!/usr/bin/env bash
set -euo pipefail
ollama pull llama3.1
ollama pull nomic-embed-text
ollama pull llama3.2:3b || true
ollama pull qwen2.5:7b || true
ollama pull qwen2.5-coder:7b || true
if [[ "${PULL_LARGE:-0}" == "1" ]]; then
  ollama pull llama3.1:70b || true
  ollama pull qwen2.5:32b || true
fi
if ollama list 2>/dev/null | grep -qi bggpt; then
  ROOT="$(cd "$(dirname "$0")/.." && pwd)"
  ollama create bggpt-legal -f "$ROOT/deploy/Modelfile.bggpt-legal" || true
fi
ollama list
