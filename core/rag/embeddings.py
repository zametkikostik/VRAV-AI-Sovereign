"""Embedding backends for skill RAG."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import List, Optional

import httpx

from config.settings import settings

logger = logging.getLogger("vrav.rag.embed")
TOKEN_RE = re.compile(r"[a-zа-я0-9]{2,}", re.I)


def _tokenize(text: str) -> List[str]:
    return TOKEN_RE.findall((text or "").lower())


def cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)


class Embedder:
    def __init__(self, model: Optional[str] = None, dim: int = 256):
        self.model = model or "nomic-embed-text"
        self.dim = dim
        self.ollama_url = settings.ollama_base_url

    async def embed(self, text: str) -> List[float]:
        text = (text or "")[:8000]
        try:
            vec = await self._ollama_embed(text)
            if vec:
                return vec
        except Exception as e:
            logger.debug("Ollama embed failed: %s", e)
        return self._hash_embed(text)

    async def _ollama_embed(self, text: str) -> Optional[List[float]]:
        url = f"{self.ollama_url.rstrip('/')}/api/embeddings"
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, json={"model": self.model, "prompt": text})
            if resp.status_code != 200:
                return None
            data = resp.json()
            emb = data.get("embedding")
            if isinstance(emb, list) and emb:
                return [float(x) for x in emb]
        return None

    def _hash_embed(self, text: str) -> List[float]:
        vec = [0.0] * self.dim
        tokens = _tokenize(text)
        if not tokens:
            return vec
        for tok in tokens:
            h = int(hashlib.md5(tok.encode("utf-8")).hexdigest(), 16)
            idx = h % self.dim
            sign = 1.0 if (h >> 8) & 1 else -1.0
            vec[idx] += sign
        norm = math.sqrt(sum(x * x for x in vec)) or 1.0
        return [x / norm for x in vec]


embedder = Embedder()
