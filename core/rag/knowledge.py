"""
Unified Knowledge Layer — Ollama embeddings + vector RAG over corpus, skills, and facts.

Goal: agent can *retrieve* relevant knowledge before answering (not claim omniscience).
Falls back to hash embeddings when Ollama embed model is unavailable.
"""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from config.settings import settings
from core.rag.doc_index import doc_rag
from core.rag.skill_index import skill_rag

logger = logging.getLogger("vrav.rag.knowledge")

ROOT = Path(__file__).resolve().parents[2]
CACHE_PATH = ROOT / "data" / "rag" / "web_cache.json"


class KnowledgeLayer:
    def __init__(self, min_score: float = 0.12, top_k_docs: int = 5, top_k_skills: int = 3):
        self.min_score = min_score
        self.top_k_docs = top_k_docs
        self.top_k_skills = top_k_skills
        self._web_cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self) -> None:
        try:
            if CACHE_PATH.exists():
                self._web_cache = json.loads(CACHE_PATH.read_text(encoding="utf-8"))
        except Exception:
            self._web_cache = {}

    def _save_cache(self) -> None:
        try:
            CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
            items = list(self._web_cache.items())[-200:]
            CACHE_PATH.write_text(json.dumps(dict(items), ensure_ascii=False), encoding="utf-8")
        except OSError:
            pass

    def cache_web(self, query: str, results: Any, ttl_sec: int = 3600) -> None:
        key = (query or "")[:200].lower().strip()
        if not key:
            return
        self._web_cache[key] = {"ts": time.time(), "ttl": ttl_sec, "results": results}
        self._save_cache()

    def get_cached_web(self, query: str) -> Optional[Any]:
        key = (query or "")[:200].lower().strip()
        entry = self._web_cache.get(key)
        if not entry:
            return None
        if time.time() - float(entry.get("ts", 0)) > float(entry.get("ttl", 3600)):
            return None
        return entry.get("results")

    async def ensure_indexed(self, force: bool = False) -> Dict[str, int]:
        stats = {"docs": 0, "skills": 0}
        try:
            if force or not getattr(doc_rag, "_chunks", None):
                result = await doc_rag.reindex()
                stats["docs"] = int(result.get("chunks") or result.get("indexed") or 0)
            else:
                stats["docs"] = len(getattr(doc_rag, "_chunks", []) or [])
        except Exception as e:
            logger.warning("doc reindex: %s", e)
        try:
            n = await skill_rag.reindex()
            stats["skills"] = int(n or 0)
        except Exception as e:
            logger.warning("skill reindex: %s", e)
        return stats

    async def retrieve(self, query: str) -> Dict[str, Any]:
        query = (query or "").strip()
        sources: List[Dict[str, Any]] = []
        doc_hits: List[Dict[str, Any]] = []
        skill_hits: List[Dict[str, Any]] = []
        try:
            doc_hits = await doc_rag.retrieve(query, top_k=self.top_k_docs, min_score=self.min_score)
            for h in doc_hits:
                sources.append({
                    "type": "corpus",
                    "title": h.get("source") or h.get("file") or "doc",
                    "score": round(float(h.get("score") or 0), 3),
                    "snippet": (h.get("text") or h.get("content") or "")[:240],
                })
        except Exception as e:
            logger.debug("doc retrieve: %s", e)
        try:
            skill_hits = await skill_rag.retrieve(
                query, top_k=self.top_k_skills, min_score=max(0.12, self.min_score - 0.05)
            )
            for h in skill_hits:
                sources.append({
                    "type": "skill",
                    "title": h.get("name") or "skill",
                    "score": round(float(h.get("score") or 0), 3),
                    "snippet": (h.get("content") or h.get("description") or "")[:240],
                })
        except Exception as e:
            logger.debug("skill retrieve: %s", e)
        try:
            from core.memory.store import memory_store
            facts = memory_store.get_facts() or []
            q_tokens = set(query.lower().split())
            for f in facts[:50]:
                blob = f"{f.get('key', '')} {f.get('value', '')}".lower()
                if q_tokens & set(blob.split()):
                    sources.append({
                        "type": "memory",
                        "title": f.get("key") or "fact",
                        "score": 0.4,
                        "snippet": str(f.get("value") or "")[:200],
                    })
        except Exception:
            pass
        sources.sort(key=lambda x: x.get("score", 0), reverse=True)
        return {
            "query": query,
            "doc_hits": doc_hits,
            "skill_hits": skill_hits,
            "sources": sources[:12],
            "grounding_score": max((s.get("score") or 0) for s in sources) if sources else 0.0,
        }

    def format_for_prompt(self, retrieval: Dict[str, Any], max_chars: int = 6000) -> str:
        parts: List[str] = []
        for h in retrieval.get("doc_hits") or []:
            src = h.get("source") or h.get("file") or "corpus"
            text = h.get("text") or h.get("content") or ""
            parts.append(f"[corpus:{src} score={h.get('score', 0):.2f}]\n{text}")
        for h in retrieval.get("skill_hits") or []:
            name = h.get("name") or "skill"
            text = h.get("content") or h.get("description") or ""
            parts.append(f"[skill:{name} score={h.get('score', 0):.2f}]\n{text}")
        block = "\n\n".join(parts)
        if len(block) > max_chars:
            block = block[:max_chars] + "\n…[truncated]"
        if not block:
            return ""
        return (
            "## Retrieved knowledge (vector RAG — cite when used; do not invent beyond this)\n"
            + block
        )


knowledge = KnowledgeLayer(min_score=float(getattr(settings, "rag_min_score", 0.12) or 0.12))
