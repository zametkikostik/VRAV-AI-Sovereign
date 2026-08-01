"""Hard vector filtering (RAG) over distilled skills."""

from __future__ import annotations

import json
import logging
import time
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.rag.embeddings import cosine, embedder
from core.skills.manager import skill_manager

logger = logging.getLogger("vrav.rag.skills")
INDEX_PATH = Path(__file__).resolve().parents[2] / "data" / "rag" / "skill_vectors.json"


class SkillRAG:
    def __init__(self, min_score: float = 0.28, top_k: int = 5):
        self.min_score = min_score
        self.top_k = top_k
        self.index_path = INDEX_PATH
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            try:
                self._cache = json.loads(self.index_path.read_text(encoding="utf-8"))
            except Exception:
                self._cache = {}

    def _save(self) -> None:
        try:
            self.index_path.write_text(json.dumps(self._cache, ensure_ascii=False), encoding="utf-8")
        except OSError as e:
            logger.warning("Cannot persist skill vectors: %s", e)

    async def reindex(self) -> int:
        skills = skill_manager.list_skills()
        count = 0
        names = {s.get("name") for s in skills if s.get("name")}
        for path in skill_manager.root.glob("*.md"):
            names.add(path.stem)
        for name in names:
            body = skill_manager.get_skill(name) or ""
            meta = next((s for s in skills if s.get("name") == name), {})
            text = f"{name}\n{meta.get('description', '')}\n{body}"
            vec = await embedder.embed(text)
            self._cache[name] = {
                "name": name,
                "description": meta.get("description") or name,
                "vector": vec,
                "updated_at": time.time(),
                "preview": (body or meta.get("description") or "")[:400],
            }
            count += 1
        self._save()
        return count

    async def ensure_indexed(self, name: str, text: str) -> None:
        vec = await embedder.embed(text)
        self._cache[name] = {
            "name": name,
            "description": text[:200],
            "vector": vec,
            "updated_at": time.time(),
            "preview": text[:400],
        }
        self._save()

    async def retrieve(
        self, query: str, top_k: Optional[int] = None, min_score: Optional[float] = None,
    ) -> List[Dict[str, Any]]:
        if not self._cache:
            await self.reindex()
        qvec = await embedder.embed(query)
        scored: List[Tuple[float, Dict[str, Any]]] = []
        for name, entry in self._cache.items():
            score = cosine(qvec, entry.get("vector") or [])
            scored.append((score, entry))
        scored.sort(key=lambda x: x[0], reverse=True)
        k = top_k or self.top_k
        threshold = min_score if min_score is not None else self.min_score
        results = []
        for score, entry in scored[: max(k * 3, k)]:
            if score < threshold:
                continue
            body = skill_manager.get_skill(entry["name"])
            results.append({
                "name": entry["name"],
                "score": round(score, 4),
                "description": entry.get("description"),
                "content": body or entry.get("preview") or "",
            })
            if len(results) >= k:
                break
        return results

    def format_for_prompt(self, skills: List[Dict[str, Any]]) -> str:
        if not skills:
            return "## Retrieved skills\n(none above similarity threshold — do not invent procedures)"
        lines = ["## Retrieved skills (RAG — use only these procedures)"]
        for s in skills:
            lines.append(f"### {s['name']} (score={s['score']})")
            lines.append((s.get("content") or s.get("description") or "")[:1200])
        return "\n".join(lines)


skill_rag = SkillRAG(min_score=0.28, top_k=4)
