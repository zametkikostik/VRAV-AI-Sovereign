# Source sync status

Repository: https://github.com/zametkikostik/VRAV-AI-Sovereign

## On GitHub now
- Bootstrap: README, LICENSE, Dockerfile, compose, requirements, main.py
- Auth (API keys / users)
- React SPA (`web/`)
- Agents, RAG embeddings, policy, quotas, SSE helpers, research MCP tools
- Package layout + many `__init__.py`

## Still denser on local full tree (to finish uploading)
Large modules may still be incomplete on remote until fully pushed:
- `core/orchestrator.py`, `core/agent_loop.py`
- `core/delegate/coordinator.py`, `persistent.py`
- `core/sandbox/runner.py`, `core/safety/guard.py`, `injection.py`, `shield.py`
- `core/mcp/protocol.py`, `builtin_tools.py`
- `core/rag/skill_index.py`, `core/research/web.py`, `core/memory/store.py`
- `core/skills/*`, `core/tools/*`, `core/sessions/store.py`, `core/workspace/bootstrap.py`
- `static/*` UI, remaining tests

## Full local archive
Complete source is available as `VRAV-AI-Sovereign-source.tar.gz` from the build workspace.

```bash
git clone https://github.com/zametkikostik/VRAV-AI-Sovereign.git
# overlay full archive if needed, then:
pip install -r requirements.txt
uvicorn main:app --port 8000
```
