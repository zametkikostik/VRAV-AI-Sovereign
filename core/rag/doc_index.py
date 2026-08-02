"""Document RAG indexer for user files under data/corpus."""

from __future__ import annotations

import hashlib
import json
import logging
import re
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.rag.embeddings import cosine, embedder

logger = logging.getLogger("vrav.rag.docs")
ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CORPUS = ROOT / "data" / "corpus"
INDEX_PATH = ROOT / "data" / "rag" / "doc_vectors.json"
TEXT_EXTS = {".txt", ".md", ".markdown", ".json", ".csv", ".html", ".htm", ".log", ".rst"}
CHUNK_SIZE = 900
CHUNK_OVERLAP = 120


def _read_text_file(path: Path) -> str:
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("read fail %s: %s", path, e)
        return ""


def _read_pdf(path: Path) -> str:
    try:
        from pypdf import PdfReader
    except ImportError:
        try:
            from PyPDF2 import PdfReader  # type: ignore
        except ImportError:
            logger.warning("PDF skipped (install pypdf): %s", path)
            return ""
    try:
        reader = PdfReader(str(path))
        return "\n".join((p.extract_text() or "") for p in reader.pages)
    except Exception as e:
        logger.warning("pdf fail %s: %s", path, e)
        return ""


def extract_text(path: Path) -> str:
    suf = path.suffix.lower()
    if suf in TEXT_EXTS:
        return _read_text_file(path)
    if suf == ".pdf":
        return _read_pdf(path)
    return ""


def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    text = re.sub(r"\s+", " ", (text or "").strip())
    if not text:
        return []
    if len(text) <= size:
        return [text]
    chunks, i = [], 0
    while i < len(text):
        chunks.append(text[i : i + size])
        i += max(1, size - overlap)
    return chunks


class DocRAG:
    def __init__(self, corpus_dir=None, index_path=None, min_score: float = 0.22, top_k: int = 6):
        self.corpus_dir = Path(corpus_dir or DEFAULT_CORPUS)
        self.index_path = Path(index_path or INDEX_PATH)
        self.min_score = min_score
        self.top_k = top_k
        self.corpus_dir.mkdir(parents=True, exist_ok=True)
        self.index_path.parent.mkdir(parents=True, exist_ok=True)
        self._chunks: List[Dict[str, Any]] = []
        self._load()

    def _load(self) -> None:
        if self.index_path.exists():
            try:
                data = json.loads(self.index_path.read_text(encoding="utf-8"))
                self._chunks = data.get("chunks") or []
            except Exception:
                self._chunks = []

    def _save(self) -> None:
        payload = {
            "updated_at": time.time(),
            "corpus": str(self.corpus_dir),
            "n_chunks": len(self._chunks),
            "chunks": self._chunks,
        }
        self.index_path.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    def list_files(self) -> List[str]:
        if not self.corpus_dir.exists():
            return []
        return [
            str(p.relative_to(self.corpus_dir))
            for p in sorted(self.corpus_dir.rglob("*"))
            if p.is_file() and not p.name.startswith(".")
        ]

    async def reindex(self, force: bool = False) -> Dict[str, Any]:
        files, new_chunks = [], []
        for path in sorted(self.corpus_dir.rglob("*")):
            if not path.is_file() or path.name.startswith("."):
                continue
            text = extract_text(path)
            if not text.strip():
                continue
            rel = str(path.relative_to(self.corpus_dir))
            files.append(rel)
            for i, part in enumerate(chunk_text(text)):
                cid = hashlib.sha1(f"{rel}:{i}:{part[:80]}".encode()).hexdigest()[:16]
                vec = await embedder.embed(part)
                new_chunks.append({"id": cid, "source": rel, "chunk_i": i, "text": part, "vector": vec})
        self._chunks = new_chunks
        self._save()
        return {"files": len(files), "chunks": len(new_chunks), "corpus": str(self.corpus_dir), "index": str(self.index_path)}

    async def retrieve(self, query: str, top_k: Optional[int] = None, min_score: Optional[float] = None) -> List[Dict[str, Any]]:
        if not self._chunks:
            self._load()
        if not self._chunks:
            return []
        k = top_k or self.top_k
        thr = min_score if min_score is not None else self.min_score
        qvec = await embedder.embed(query)
        scored = []
        for ch in self._chunks:
            s = cosine(qvec, ch.get("vector") or [])
            if s >= thr:
                scored.append({
                    "id": ch["id"], "source": ch["source"], "score": round(float(s), 4),
                    "text": ch["text"], "chunk_i": ch.get("chunk_i", 0),
                })
        scored.sort(key=lambda x: x["score"], reverse=True)
        return scored[:k]

    def format_for_prompt(self, hits: List[Dict[str, Any]]) -> str:
        if not hits:
            return ""
        lines = ["## Retrieved documents (RAG)"]
        for h in hits:
            lines.append(f"- ({h['score']}) {h['source']}#{h.get('chunk_i', 0)}")
            lines.append(h["text"][:600])
        return "\n".join(lines)


doc_rag = DocRAG()
