# VRAV AI — Sync Status

**Repo:** https://github.com/zametkikostik/VRAV-AI-Sovereign  
**Version:** 0.9.0

## Quality pass (2026-08-02)

- **69 offline tests green**
- Fixed circular import: `BaseAgent` ↔ `AgentOrchestrator`
- Provider routing: **prefer_ollama=True** by default (sovereign)
- OpenRouter missing key → soft fallback to Ollama (no hard 503)
- SSRF: blocked RFC1918, CGNAT, link-local, `.local` / `.internal`, cloud metadata
- Agent loop injects workspace SOUL/AGENTS block
- Settings: `data_dir`, `auth_mode`, `max_tool_rounds`, auto-create dirs
- Domain tool tests use `asyncio.run`

## How to run

```bash
cp .env.example .env
pip install -r requirements.txt
# start Ollama + pull llama3.1
uvicorn main:app --reload
# open http://localhost:8000/
pytest tests/ -q --ignore=tests/test_e2e_ollama.py
```

## Safety invariants
1. No OpenAI / Anthropic clients
2. InjectionGuard before LLM
3. PolicyGate on tools & text
4. Sandbox AST allowlist + optional Docker network=none
5. Anti-hallucination RAG grounding
6. Web results tagged untrusted_source
