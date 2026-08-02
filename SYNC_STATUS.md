# VRAV AI — GitHub Sync Status

**Repo:** https://github.com/zametkikostik/VRAV-AI-Sovereign  
**Updated:** 2026-08-02

## Synced this session (batches)

### Safety & core
- `main.py` — v0.8 SPA mount + Auth + Shield middleware
- `core/agent_loop.py` — ReAct tool-calling SSE loop
- `core/sandbox/runner.py` — AST whitelist + Docker/gVisor/seccomp + quotas
- `core/sandbox/quotas.py`
- `core/safety/guard.py` — RAG grounding + fact-check
- `core/safety/injection.py` — multi-layer injection shield
- `core/safety/policy.py` — harmful action PolicyGate
- `core/safety/shield.py` — code safety + encrypted append-only logs + rate limit
- `core/safety/rate_limit.py`

### UI & deploy
- `docker-compose.yml` — ollama + api + model init
- `Dockerfile`, `requirements.txt`, `.env.example`
- `web/` React SPA — theme toggle, API key, agent/stream/delegate
- `static/index.html`, `static/css/app.css`, `static/js/app.js` — Open WebUI panels
- `README.md` — full v0.2–v0.8 feature docs

### Already on main (prior batches)
- Full `core/` tree: auth, mcp, memory, rag, research, sessions, skills, streaming, tools, workspace, delegate, agents
- `core/orchestrator.py` — present with stream/SSE, agent loop, MCP, sessions, RAG, sandbox endpoints
- `tests/`, `evals/`, `deploy/`, CI workflow
- `data/workspace/` SOUL.md · AGENTS.md · IDENTITY.md · USER.md

## Status
**Primary codebase is on GitHub.** Local may have minor doc-RAG extras in orchestrator; remote covers all public API routes and safety invariants.

## Safety invariants (always on)
1. No OpenAI / Anthropic direct clients
2. Prompt-injection blocked before LLM
3. PolicyGate hard-denies harmful tools/content
4. Code sandbox: AST allowlist + optional Docker `network=none`
5. Anti-hallucination: Pydantic + RAG grounding + optional Serper
