# VRAV AI — Sovereign Agentic Orchestrator

Независима, суверенна платформа за оркестрация на ИИ-агенти.  
**Няма OpenAI / Anthropic.** Поддържа Ollama (локално), OpenRouter и BgGPT.

## Архитектура

```
core/
  orchestrator.py      # Асинхронен движок (Reason + Act)
  safety/
    guard.py           # Anti-Hallucination + web fact-check
    shield.py          # Prompt Injection + Code Safety + encrypted logs
  tools/
    openapi_discovery.py  # Автоматично подключване на Swagger/OpenAPI
  agents/
    base.py            # Шаблон за нови агенти
    legal_bg.py        # Пример: правен агент за България/ЕС
  models/schemas.py    # Pydantic модели
```

## Быстрый старт

### 1. Локально (без Docker)

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # заполни ключи
uvicorn main:app --reload
```

Ollama трябва да слуша на `localhost:11434`.

### 2. Docker Compose (препоръчително)

```bash
cp .env.example .env
docker compose up -d
# API → http://localhost:8000
# Docs → http://localhost:8000/docs
```

Първото стартиране ще изтегли `llama3.1` в Ollama.

## API

`POST /api/stream`

```json
{
  "prompt": "Какъв е данъкът върху добавената стойност в България?",
  "model": "bggpt",
  "temperature": 0.3
}
```

`GET /api/health`

## Безопасност

- Prompt Injection Shield (многослоен regex + блокиране)
- Code Safety Filter (блокира `rm -rf`, `eval`, reverse shells и т.н.)
- Append-only encrypted event log (Fernet) — устойчивост към централизиран спарсинг
- Fact-check contour за факти, дати, закони (Bg/EU приоритет)

## Тестове

```bash
pytest tests/ -v
```

## Добавяне на нов агент

```python
from core.agents.base import BaseAgent

class MyAgent(BaseAgent):
    name = "my_agent"
    system_prompt = "..."
    preferred_model = "llama3.1"

    async def preprocess(self, user_input: str) -> str:
        return user_input
```

## OpenAPI Tools

```python
from core.tools.openapi_discovery import discovery

tools = await discovery.discover("https://petstore.swagger.io/v2/swagger.json")
result = await discovery.call_tool("get_pet_by_id", {"petId": 1})
```

---
VRAV AI — суверенитет + гъвкавост + защита.

## v0.2 — Streaming, Memory, Skills, EUR-Lex

### SSE Streaming
```bash
curl -N -X POST http://localhost:8000/api/stream/sse \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Какво казва GDPR член 17?"}'
```

Events: `status`, `session`, `tool`, `token`, `done`, `error`.

### Memory
- Episodic sessions (SQLite)
- Semantic facts + `data/memory/MEMORY.md`
- Endpoints: `GET /api/memory/facts`

### Self-learning (Hermes-style)
After 3 similar successful tasks → auto-distills `data/skills/<name>.md`
- `GET /api/skills`

### EUR-Lex
- `GET /api/eurlex/{celex}` e.g. `/api/eurlex/32016R0679`
- Auto-invoked when prompt mentions CELEX / GDPR article / EU law

### Hardened injection
Multi-layer `InjectionGuard`: patterns, role-confusion, base64 smuggling, density score, output canary.

## v0.3 — True stream · Skill review · Workspace · CELLAR

### 1. True token stream (Ollama `stream: true`)
`POST /api/stream/sse` now streams real model tokens via:
- `core/streaming/ollama_stream.py` → NDJSON from Ollama
- OpenRouter SSE deltas when routed externally

### 2. Background skill-review
After every successful reply, `schedule_review()` enqueues a non-blocking job:
- extracts durable facts → memory
- decides if pattern is skill-worthy
- distills or refines skills (`core/skills/reviewer.py`)

### 3. OpenClaw-style workspace
Files under `data/workspace/`:
| File | Role |
|------|------|
| SOUL.md | persona, boundaries, tone |
| AGENTS.md | operating policy |
| IDENTITY.md | name / vibe |
| USER.md | user profile |
| BOOTSTRAP.md | first-run (auto-deleted) |
| MEMORY.md | long-term (also via MemoryStore) |

`GET /api/workspace` — inspect injection set.

### 4. CELLAR SPARQL
Official EU Publications Office endpoint:
- `GET /api/cellar/search?q=GDPR`
- `GET /api/eurlex/{celex}` returns HTML + CELLAR metadata
- Auto-invoked in orchestrator for legal prompts


## v0.4 — LLM skill review · Multi-agent · MCP tools

### LLM-powered skill reviewer
`core/skills/llm_reviewer.py`
- Background review uses Ollama with structured JSON actions
- Falls back to heuristics if model unavailable
- Actions: `create_skill`, `refine_skill`, `upsert_fact`, `skip`

### Multi-agent delegate
`POST /api/delegate`
```json
{"prompt": "Какво казва GDPR чл. 17?", "parallel": true}
```
Sub-agents: **legal**, **research**, **coding**, **critic**  
Uses MCP tools for EUR-Lex/CELLAR context.

### MCP-compatible tool layer
| Endpoint | Purpose |
|----------|---------|
| `POST /api/mcp` | JSON-RPC 2.0 (`initialize`, `tools/list`, `tools/call`) |
| `GET /api/mcp/tools` | List tools |
| `POST /api/mcp/tools/call` | Direct call `{"name","arguments"}` |

Built-in tools: `eurlex_get`, `cellar_search`, `gdpr_article`, `memory_*`, `skills_list`, `echo`.


## v0.5 — Tool-calling agent · Persistent sessions · Safe web learning

### Philosophy
The agent can **research the public web**, learn facts into memory/skills, and help people —
but **cannot** run destructive actions, produce malware/exploits, or obey injection payloads
found on web pages (treated as untrusted data).

### Agent tool-calling loop (SSE)
```bash
curl -N -X POST http://localhost:8000/api/agent/sse \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Какво е GDPR накратко? Провери в Wikipedia."}'
```
Events: `status` → `tool_call` → `tool_result` → … → `token` → `done`

Tools the model may choose: `web_search`, `web_fetch`, `wiki_summary`, `eurlex_*`, `cellar_search`, memory/skills.

### Persistent multi-agent sessions
```bash
# Start
curl -X POST /api/sessions -d '{"prompt":"..."}'
# Continue later
curl -X POST /api/sessions/{id}/continue -d '{"prompt":"уточни точка 2"}'
# Inspect / list / close
GET /api/sessions
GET /api/sessions/{id}
POST /api/sessions/{id}/close
```

### Safety stack
1. InjectionGuard (input)
2. PolicyGate (harmful goals & tool args)
3. Read-only research tools (no shell, no code exec of fetched pages)
4. SSRF protection (no localhost / private IPs)
5. CodeSafetyFilter + output canary
6. Web results tagged `untrusted_source`


## v0.6 — Skill RAG · Anti-hallucination grounding · Code sandbox

### Hard vector skill filtering (RAG)
- `core/rag/embeddings.py` — Ollama embeddings or local hash vectors
- `core/rag/skill_index.py` — cosine filter, `min_score` gate
- MultiAgentDelegate injects **only** skills above threshold
- `POST /api/rag/reindex` · `GET /api/rag/skills?q=...`

### Anti-hallucination (exists + strengthened)
- Claim detection + optional Serper check
- **RAG grounding score** vs retrieved skills / tool context
- Low grounding → confidence drop + warning banner

### Code sandbox (whitelist)
- `POST /api/sandbox/run` `{"code": "...", "docker": false}`
- AST allowlist, blocked dunders/eval/open/os
- Imports: math, json, re, datetime, collections, statistics, decimal only
- Optional Docker: `--network none --memory 128m --read-only`
- MCP tool: `code_sandbox`


## v0.7 — Open WebUI-style UI + hardened sandbox

### UI
Open `http://localhost:8000/` after `uvicorn main:app`.

Panels:
- **Chat** — Agent SSE / simple stream / multi-agent modes
- **Sessions** — persistent multi-agent (start / continue / close)
- **Skills / RAG** — list + semantic search + reindex
- **Sandbox** — run whitelist code, Docker toggle, per-user quota

### Sandbox hardening
| Layer | Mechanism |
|-------|-----------|
| AST gate | allowlist nodes only |
| Imports | math/json/re/datetime/collections/statistics/decimal |
| Restricted exec | no open/eval/os/subprocess |
| Docker | `--network none`, `--cap-drop ALL`, `--read-only`, nobody user, memory/cpu/pids |
| Seccomp | Docker default seccomp profile |
| gVisor | auto `--runtime runsc` if installed |
| Quotas | 50 runs / hour, 60s CPU budget, 20KB code |

`GET /api/sandbox/quota?user_id=default`  
`POST /api/sandbox/run` `{"code","docker","user_id"}`


## v0.8 — Auth · Theme · React SPA

### Auth (API keys / users)
```bash
# Modes: AUTH_MODE=off|optional|required
export AUTH_MODE=required

# Bootstrap admin key (first run): data/auth/BOOTSTRAP_KEY.txt
curl -H "Authorization: Bearer $KEY" http://localhost:8000/api/auth/me

# Admin: create user + key
curl -H "Authorization: Bearer $KEY" -X POST /api/auth/users -d '{"username":"alice"}'
curl -H "Authorization: Bearer $KEY" -X POST /api/auth/keys -d '{"user_id":"...","name":"cli"}'
```

### Theme toggle
Built-in UI (`/` or `/app`) and React SPA: dark / light, saved in `localStorage`.

### React SPA
```bash
cd web
npm install
npm run build    # → web/dist, served at /ui/
npm run dev      # Vite dev server with /api proxy
```

Static fallback UI remains at `/app`.
