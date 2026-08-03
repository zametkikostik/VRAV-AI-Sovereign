# VRAV AI — Sovereign Agentic Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg)](https://fastapi.tiangolo.com/)
[![Tests](https://img.shields.io/badge/tests-80%2B%20offline-brightgreen.svg)](#tests--ci)
[![Coverage](https://img.shields.io/badge/coverage-CI%20enforced-informational.svg)](.github/workflows/ci.yml)
[![No OpenAI required](https://img.shields.io/badge/OpenAI%2FAnthropic-not%20required-important.svg)](#)

**EN** · **БГ** · **RU**

Sovereign AI agent orchestrator: **Ollama-first**, optional OpenRouter / BgGPT.  
No mandatory OpenAI or Anthropic. Built for privacy, EU/BG legal tools (EUR-Lex, CELLAR), and safe research agents.

> **MIT License** — free to use, fork, and commercialize.  
> **Attribution required:** *Based on VRAV AI — https://github.com/zametkikostik/VRAV-AI-Sovereign*

---

## English

### What it is
A **FastAPI** platform that runs multi-step AI agents with streaming (SSE), tools (MCP), vector RAG, sessions/memory, and hard safety rails. Default brain: **local Ollama**.

### Why it matters
| Goal | How VRAV helps |
|------|----------------|
| Coding, science, everyday help (EN/BG/RU/…) | Local LLM + tools + RAG; answers in the user’s language |
| Fewer hallucinations on facts | Web/wiki/EUR-Lex + local corpus + anti-hallucination checks |
| New knowledge without fine-tune | Drop files into `data/corpus/` → `make index`; skills after success |
| No harmful execution | PolicyGate, injection shield, AST/Docker sandbox, optional LLM classifier |
| Data sovereignty | On-prem Ollama, encrypted logs, optional Postgres for multi-replica |

### Quick start
```bash
git clone https://github.com/zametkikostik/VRAV-AI-Sovereign.git
cd VRAV-AI-Sovereign
bash scripts/quickstart.sh
# or: make quickstart && make run
# → http://127.0.0.1:8000
```

```bash
ollama pull llama3.1 && ollama pull nomic-embed-text
bash scripts/pull-models.sh
```

**Docker:** `docker compose up -d --build`  
**Production:** `docker compose -f docker-compose.prod.yml up -d --build`  
**Public TLS:** see [deploy/public-server.md](deploy/public-server.md) · `AUTH_MODE=required`

### Roadmap status
| Item | Status |
|------|--------|
| PostgreSQL backend (multi-replica memory) | ✅ `DATABASE_URL=postgresql://…` |
| Optional LLM safety classifier | ✅ `ENABLE_LLM_SAFETY_CLASSIFIER=true` |
| Coverage in CI + security test suite | ✅ `--cov` + `tests/test_security_suite.py` |
| CONTRIBUTING + community templates | ✅ [CONTRIBUTING.md](CONTRIBUTING.md) · issue templates |
| MIT license + attribution | ✅ [LICENSE](LICENSE) · [NOTICE](NOTICE) |

### Architecture (short)
```
UI (static / React) → FastAPI orchestrator + ReAct tool-loop
                   → Knowledge RAG + MCP tools + memory/skills
                   → Safety (injection · policy · sandbox · optional LLM guard)
                   → Ollama ★ / OpenRouter / BgGPT
```

### Tests & CI
```bash
make test
pytest tests/test_security_suite.py -q
PYTHONPATH=. python evals/offline_rag_eval.py
```
CI runs offline tests, coverage gate, syntax check, sandbox smoke; optional live Ollama E2E.

### License
MIT © zametkikostik / contributors. Credit the project in forks and products:

> Based on [VRAV AI](https://github.com/zametkikostik/VRAV-AI-Sovereign)

---

## Български

### Какво е това
**Суверенна** платформа за оркестрация на ИИ-агенти (FastAPI): локални модели чрез **Ollama**, по желание OpenRouter / BgGPT. Без задължителен OpenAI/Anthropic. Интеграции с **EUR-Lex** и **CELLAR**, защита от инжекции, sandbox, RAG върху собствен корпус.

### За кого
- Юристи / екипи с GDPR и българско право  
- Екипи, които искат **локален** асистент (код, изследвания, документи)  
- Хора, за които суверенитетът на данните е важен  

### Бърз старт
```bash
git clone https://github.com/zametkikostik/VRAV-AI-Sovereign.git
cd VRAV-AI-Sovereign
bash scripts/quickstart.sh
make run
# → http://127.0.0.1:8000
```

Модели: `ollama pull llama3.1` и `nomic-embed-text`.  
Правни бележки в `data/corpus/` (GDPR, КЗЛД, КТ, …) — добавяйте свои PDF/MD и `make index`.

### Статус на roadmap
| Точка | Статус |
|-------|--------|
| PostgreSQL за multi-replica | ✅ |
| Опционален LLM safety classifier | ✅ |
| Coverage в CI + security suite | ✅ |
| CONTRIBUTING / community | ✅ |
| MIT + атрибуция | ✅ |

### Лиценз
MIT — свободна употреба, включително търговска. **Задължително посочване на източника** (виж [LICENSE](LICENSE)).

---

## Русский

### Что это
Суверенный оркестратор ИИ-агентов: **Ollama** локально, опционально OpenRouter / BgGPT. Без обязательного OpenAI/Anthropic. Безопасность, EU/BG-право (EUR-Lex, CELLAR), RAG, skills, sandbox.

### Цели пользователей
| Цель | Как |
|------|-----|
| Код и задачи на RU/BG/EN | Модель + tools; ответ на языке запроса |
| Не «тупить» на фактах | Web/wiki/EUR-Lex + `data/corpus/` |
| Новые знания | Файлы в корпус → индекс; memory/skills; agent tools |
| Без вреда | Policy + injection + sandbox + опциональный LLM-классификатор |

### Быстрый старт
```bash
bash scripts/quickstart.sh && make run
```

### Roadmap
| Пункт | Статус |
|-------|--------|
| PostgreSQL multi-replica | ✅ `DATABASE_URL` |
| Optional LLM safety classifier | ✅ |
| Coverage + security suite | ✅ |
| CONTRIBUTING · community | ✅ |
| MIT + указание источника | ✅ |

### Лицензия
MIT — можно пользоваться и в коммерции. **Указывайте источник:**  
*Based on VRAV AI — https://github.com/zametkikostik/VRAV-AI-Sovereign*

---

## Config snippets

```bash
DATABASE_URL=postgresql://vrav:vrav@postgres:5432/vrav
ENABLE_LLM_SAFETY_CLASSIFIER=true
SAFETY_CLASSIFIER_MODEL=llama-guard3
AUTH_MODE=required
```

```bash
docker compose -f docker-compose.prod.yml --profile postgres up -d
```

---

## Author

**zametkikostik** · [github.com/zametkikostik/VRAV-AI-Sovereign](https://github.com/zametkikostik/VRAV-AI-Sovereign)

PRs welcome — keep [LICENSE](LICENSE) / [NOTICE](NOTICE) and follow [CONTRIBUTING.md](CONTRIBUTING.md).
