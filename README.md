# VRAV AI — Sovereign Agentic Orchestrator

Independent, privacy-first multi-agent platform.
**No OpenAI / Anthropic direct APIs.** Ollama · OpenRouter · BgGPT.

## Quick start

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --host 0.0.0.0 --port 8000
```

UI: http://localhost:8000/  ·  API docs: /docs

## Features

- SSE streaming (true Ollama token stream)
- Agent tool-calling loop (MCP tools)
- Multi-agent delegate + persistent sessions
- Skill RAG (vector filter)
- Anti-hallucination + injection shield
- Safe code sandbox (whitelist / Docker / quotas)
- Auth (API keys / users)
- Static UI + React SPA (`web/`)

## Auth

`AUTH_MODE=off|optional|required`

Bootstrap admin key on first run: `data/auth/BOOTSTRAP_KEY.txt`

## React SPA

```bash
cd web && npm i && npm run build
# served at /ui/
```

## License

MIT — sovereign by design.
