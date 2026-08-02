# Document corpus for VRAV RAG

Put `.txt`, `.md`, `.pdf`, `.html`, `.csv`, `.json` here.

```bash
PYTHONPATH=. python scripts/index_docs.py
PYTHONPATH=. python scripts/index_docs.py --query "GDPR срок"
```

API: `POST /api/docs/reindex`, `GET /api/docs/search?q=...`
MCP: `doc_search`, `doc_reindex`
