# VRAV AI — GitHub Sync Status

**Repo:** https://github.com/zametkikostik/VRAV-AI-Sovereign  
**Last batch:** 2026-08-02

## Pushed in this session
- `main.py` (v0.8 SPA mount + auth/shield middleware)
- `core/agent_loop.py` (ReAct tool-calling SSE)
- `core/sandbox/runner.py` (AST whitelist + Docker/gVisor/seccomp + quotas)
- `core/sandbox/quotas.py`
- `core/safety/guard.py` (RAG grounding + fact-check)
- `core/safety/injection.py` (multi-layer injection shield)
- `core/safety/policy.py` (harmful action gate)
- `core/safety/shield.py` (code safety + encrypted append-only logs + rate limit)
- `core/safety/rate_limit.py`
- `docker-compose.yml` (ollama + api + init)
- `web/` React SPA (theme toggle, API key, agent/stream/delegate modes)

## Already present on main (from earlier batches)
- Full `core/` tree (auth, mcp, memory, rag, research, sessions, skills, streaming, tools, workspace, delegate, agents)
- `tests/` suite
- `static/` Open WebUI-style fallback
- `data/workspace` SOUL.md / AGENTS.md / IDENTITY.md
- `evals/`, `deploy/`, CI workflow

## Next batch candidates
- `core/orchestrator.py` (local larger than remote — needs refresh)
- `README.md` (expanded)
- `static/js/app.js`, `static/css/app.css`, `static/index.html` (fallback UI updates)
- `.env.example` (full template)

## Safety invariants (always on)
- No OpenAI / Anthropic direct clients
- Prompt-injection blocked before LLM
- PolicyGate hard-denies harmful tools/content
- Code sandbox: AST allowlist + optional Docker network=none
- Anti-hallucination: Pydantic + RAG grounding + optional Serper
