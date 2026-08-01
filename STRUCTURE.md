# VRAV AI module map

```
main.py                 # FastAPI entry, static UI + SPA mount, auth middleware
config/settings.py
core/
  auth/                 # API keys, users, AUTH_MODE
  agent_loop.py         # ReAct tool-calling SSE loop
  orchestrator.py       # routes: stream, agent, sessions, mcp, rag, sandbox
  mcp/                  # MCP JSON-RPC tools
  delegate/             # multi-agent + persistent sessions
  memory/ skills/ rag/  # memory, skill distill, vector RAG
  safety/               # injection, policy, anti-hallucination, shield
  sandbox/              # whitelist exec, docker/seccomp/gVisor, quotas
  research/ tools/      # web, EUR-Lex, CELLAR
  streaming/ workspace/ sessions/
static/                 # Open WebUI-style UI (theme + API key)
web/                    # React + Vite SPA
tests/
```

## Full source

If some modules are missing on GitHub (large push batches), the complete tree lives in the working copy / release archive `VRAV-AI-Sovereign-source.tar.gz`.

```bash
git clone https://github.com/zametkikostik/VRAV-AI-Sovereign.git
# or extract the full archive over the clone
```

## Run

```bash
pip install -r requirements.txt
cp .env.example .env
uvicorn main:app --port 8000
# optional SPA: cd web && npm i && npm run build
```
