# VRAV AI — Sovereign Agentic Orchestrator

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python 3.12+](https://img.shields.io/badge/python-3.12+-green.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-async-009688.svg)](https://fastapi.tiangolo.com/)
[![No OpenAI](https://img.shields.io/badge/OpenAI%2FAnthropic-not%20required-important.svg)](#)

**Суверенный оркестратор ИИ-агентов** — локальные модели через Ollama, опционально OpenRouter / BgGPT.  
Без обязательной привязки к OpenAI или Anthropic. Фокус: безопасность, Европа/Болгария (EUR-Lex, CELLAR), полезный research-агент.

> **Лицензия MIT** — можно использовать, форкать, встраивать в продукты, в том числе коммерчески.  
> **Обязательно указывать источник:** *Based on VRAV AI — https://github.com/zametkikostik/VRAV-AI-Sovereign*

---

## Зачем это

| Цель | Как VRAV помогает |
|------|-------------------|
| Программирование, наука, быт на **RU / BG / EN** | Ollama LLM + tools + RAG; ответ на языке пользователя |
| Не «тупить» на фактах | Web search, wiki, EUR-Lex, локальный корпус, anti-hallucination |
| Подхватывать **новые знания** | Документы в `data/corpus/` → vector RAG; skills после успешных задач; web tools |
| Не выполнять вред | PolicyGate, injection shield, sandbox (AST + Docker), read-only research |
| Суверенитет данных | Локальный Ollama, шифрованные логи, без обязательного облака |

Это **не** модель, которая «знает всё из весов». Это агент, который **достаёт** знания (корпус, сеть, инструменты) и отвечает осторожно.

---

## Быстрый старт

```bash
git clone https://github.com/zametkikostik/VRAV-AI-Sovereign.git
cd VRAV-AI-Sovereign
bash scripts/quickstart.sh
# или
make quickstart && make run
```

Открой **http://127.0.0.1:8000**

```bash
ollama pull llama3.1
ollama pull nomic-embed-text
bash scripts/pull-models.sh
PULL_LARGE=1 bash scripts/pull-models.sh   # 70B при наличии RAM/GPU
```

### Docker

```bash
cp .env.example .env
docker compose up -d --build
docker compose -f docker-compose.prod.yml up -d --build
```

Публичный сервер: [deploy/public-server.md](deploy/public-server.md) · TLS: `DOMAIN=… EMAIL=… bash deploy/tls-setup.sh` · **`AUTH_MODE=required`**.

---

## Архитектура

```
UI (static / React)  →  FastAPI orchestrator + ReAct tool-loop
                     →  Knowledge RAG + MCP tools + memory/skills
                     →  Safety (injection · policy · sandbox)
                     →  Ollama ★ / OpenRouter / BgGPT
```

**Стек:** Python 3.12 · FastAPI · Pydantic · SSE · SQLite · optional Redis · Docker sandbox.

---

## Возможности

- True token-stream из Ollama + tool-calling loop  
- Vector RAG по `data/corpus/` + skills + memory (источники в UI)  
- EUR-Lex / CELLAR SPARQL, web_search, wiki  
- Self-learning skills после успешных сессий  
- MCP tools · OpenAPI discovery  
- Sandbox: AST whitelist · Docker isolation · quotas  
- Metrics: `/api/metrics` · `/api/metrics/prometheus`  
- Auth: API keys · `AUTH_MODE=off|optional|required`  
- Voice input · export chat (UI)  

---

## Знания: код и «не тупить»

1. Сильная локальная модель — `llama3.1`, `qwen2.5-coder` для кода.  
2. Корпус — гайды и доки в `data/corpus/` → `make index`.  
3. Сеть — agent mode + tools подтягивает свежие факты (под policy).  
4. Skills — повторяющиеся сценарии сохраняются как навыки.  
5. Язык — ответ на языке пользователя (RU/BG/EN и др.).

Новые знания **не переписывают веса** на лету — они идут в **RAG / memory / skills** и доступны сразу после индексации.

---

## Безопасность (честно)

InjectionGuard · PolicyGate · CodeSafetyFilter · Sandbox · SSRF · encrypted logs.

Защита на эвристиках (не Llama Guard). Для enterprise — аудит и LLM-classifier. См. roadmap.

---

## Тесты

```bash
make test
PYTHONPATH=. python evals/offline_rag_eval.py
```

---

## Roadmap

- [ ] PostgreSQL backend для multi-replica  
- [ ] Optional LLM safety classifier  
- [ ] Coverage badge + security test suite  
- [ ] CONTRIBUTING.md · community  

---

## Лицензия

**MIT** © zametkikostik / VRAV AI contributors  

Можно использовать бесплатно, в том числе коммерчески.  
**В копиях и продуктах на базе VRAV сохраняйте LICENSE и указывайте источник:**

> Based on [VRAV AI](https://github.com/zametkikostik/VRAV-AI-Sovereign)

См. [LICENSE](LICENSE) и [NOTICE](NOTICE).

---

## Автор

**zametkikostik** · [github.com/zametkikostik/VRAV-AI-Sovereign](https://github.com/zametkikostik/VRAV-AI-Sovereign)
