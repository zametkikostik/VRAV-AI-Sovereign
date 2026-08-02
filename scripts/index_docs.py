#!/usr/bin/env python3
"""Index user documents for RAG. PYTHONPATH=. python scripts/index_docs.py"""
from __future__ import annotations
import argparse, asyncio, json, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from core.rag.doc_index import DocRAG, DEFAULT_CORPUS

async def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--corpus", default=str(DEFAULT_CORPUS))
    ap.add_argument("--query", default="")
    ap.add_argument("--top-k", type=int, default=5)
    ap.add_argument("--min-score", type=float, default=0.22)
    args = ap.parse_args()
    rag = DocRAG(corpus_dir=Path(args.corpus), min_score=args.min_score, top_k=args.top_k)
    print(f"Corpus: {rag.corpus_dir}")
    print(f"Files: {rag.list_files() or '(empty)'}")
    stats = await rag.reindex()
    print(json.dumps(stats, ensure_ascii=False, indent=2))
    if args.query:
        hits = await rag.retrieve(args.query, top_k=args.top_k, min_score=args.min_score)
        print(f"\nQuery: {args.query}")
        for h in hits:
            print(f"  [{h['score']}] {h['source']} — {h['text'][:120]}…")
        if not hits:
            print("  (no hits)")
    return 0

if __name__ == "__main__":
    raise SystemExit(asyncio.run(main()))
