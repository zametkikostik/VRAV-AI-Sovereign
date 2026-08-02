# VRAV AI v0.9.1 — Knowledge RAG

## How the agent "knows" topics
Not omniscient weights — **retrieve then answer**:
1. Vector RAG over `data/corpus/` + skills + memory (Ollama `nomic-embed-text` or hash fallback)
2. Live tools: web_search, wiki, EUR-Lex, CELLAR
3. Auto-index on startup (`rag_auto_index_on_startup`)

## New
- `core/rag/knowledge.py` — unified retrieval + web cache + sources
- SSE event `sources` for UI citations
- `GET /api/metrics`
- Expanded corpus (GDPR, KZLD, KT, AI Act, science, tech, civics)
- `evals/offline_rag_eval.py` — 100% offline with hash embeds
- 73 offline unit tests green

## Ollama embed model
```bash
ollama pull nomic-embed-text
ollama pull llama3.1
```

## Not claimed
Full world knowledge inside one model. Coverage grows with corpus + web tools under safety policy.
