# VRAV AI — GitHub Sync Status

**Repo:** https://github.com/zametkikostik/VRAV-AI-Sovereign  
**Updated:** 2026-08-02

## Batch sync: COMPLETE for core platform

### Core (uploaded)
- `core/orchestrator.py` — AgentOrchestrator + all API routes
- `core/agent_loop.py` — ReAct tool-calling SSE loop
- `core/delegate/coordinator.py` — MultiAgentDelegate + RAG filter
- `core/sandbox/runner.py` — AST whitelist + Docker/gVisor
- `core/safety/guard.py` — Anti-hallucination + RAG grounding
- `core/mcp/protocol.py` — MCP JSON-RPC
- `core/memory/store.py` — episodic + facts
- `core/research/web.py` — safe web research
- `core/skills/reviewer.py` + `llm_reviewer.py`
- `core/tools/eurlex.py` + `openapi_discovery.py`
- auth, rag, sessions, streaming, workspace, injection, policy, shield, quotas…

### UI
- `static/index.html` + `css/app.css` + `js/app.js`
- `web/` React SPA (Vite)

### Tests & config
- pytest suite, docker-compose, requirements, main.py, README

## Local full tree
`/home/workdir/artifacts/vrav_ai/`  
Also: `VRAV-AI-Sovereign-source.tar.gz`

## Run
```bash
pip install -r requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
# UI: http://localhost:8000/
# API: http://localhost:8000/docs
```
