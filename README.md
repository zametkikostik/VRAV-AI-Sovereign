# VRAV AI — Sovereign Agentic Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![codecov](https://codecov.io/gh/zametkikostik/VRAV-AI-Sovereign/branch/main/graph/badge.svg)](https://codecov.io/gh/zametkikostik/VRAV-AI-Sovereign)
[![CI](https://github.com/zametkikostik/VRAV-AI-Sovereign/actions/workflows/ci.yml/badge.svg)](https://github.com/zametkikostik/VRAV-AI-Sovereign/actions/workflows/ci.yml)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg)](https://fastapi.tiangolo.com/)
[![No OpenAI required](https://img.shields.io/badge/OpenAI%2FAnthropic-not%20required-important.svg)](#)

**EN** · **БГ** · **RU**

Sovereign AI agent orchestrator: **Ollama-first**, optional OpenRouter / BgGPT.  
No mandatory OpenAI or Anthropic. Built for privacy, EU/BG legal tools (EUR-Lex, CELLAR), and safe research agents.

> **MIT License** — free to use, fork, and commercialize.  
> **Attribution required:** *Based on VRAV AI — https://github.com/zametkikostik/VRAV-AI-Sovereign*

---

## English

### Quick start
```bash
git clone https://github.com/zametkikostik/VRAV-AI-Sovereign.git
cd VRAV-AI-Sovereign
bash scripts/quickstart.sh && make run
# → http://127.0.0.1:8000
```

### Features
- SSE agent tool-loop + **multi-agent delegate** (`/api/delegate/sse`) with **parallel interleaved token stream**
- Vector RAG (`data/corpus/`) + skills + memory
- Safety: injection, policy, sandbox, optional LLM classifier
- Optional PostgreSQL (`DATABASE_URL`), Redis rate-limit, Prometheus metrics
- Codecov coverage upload in CI (set `CODECOV_TOKEN` secret)

### Community
See [COMMUNITY.md](COMMUNITY.md) · [CONTRIBUTING.md](CONTRIBUTING.md)

### License
MIT © zametkikostik — credit the project in forks/products.

---

## Български

Суверенна платформа за ИИ-агенти (Ollama, EUR-Lex/CELLAR, GDPR/КЗЛД корпус).  
Бърз старт: `bash scripts/quickstart.sh && make run`  
Лиценз MIT — посочвайте източника.

---

## Русский

Суверенный оркестратор: локальный Ollama, RAG, multi-agent, sandbox.  
`bash scripts/quickstart.sh && make run`  
MIT — указывайте источник: VRAV AI.

---

**Author:** [zametkikostik](https://github.com/zametkikostik/VRAV-AI-Sovereign)
