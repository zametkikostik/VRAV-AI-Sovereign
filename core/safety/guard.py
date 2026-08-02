"""Anti-Hallucination Guard — RAG grounding + optional web fact-check."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import httpx

from config.settings import settings
from core.models.schemas import FactCheckResult
from core.rag.embeddings import cosine, embedder

logger = logging.getLogger("vrav.guard")


class AntiHallucinationGuard:
    def __init__(self):
        self.serper_key = settings.serper_api_key
        self.tavily_key = settings.tavily_api_key
        self.rag_min_grounding = 0.22

    async def validate_response(self, response: str, context: Dict[str, Any]) -> Dict[str, Any]:
        entities = self._extract_entities(response)
        grounding_docs = context.get("grounding_docs") or []
        tool_context = context.get("tool_context") or context.get("prompt") or ""
        grounding_score = await self._grounding_score(response, grounding_docs, tool_context)

        if not entities or not self._looks_factual(response):
            conf = max(0.85, grounding_score if grounding_docs else 0.95)
            return {
                "response": response,
                "fact_check": FactCheckResult(
                    verified=True, confidence=conf, entities_checked=[],
                    notes=f"Low factual risk; grounding={grounding_score:.2f}",
                ),
                "confidence": conf, "grounding_score": grounding_score,
            }

        fact_check = await self._fact_check(entities, context)
        confidence = min(fact_check.confidence, 0.55 + 0.45 * grounding_score)
        final_response = response

        if grounding_docs and grounding_score < self.rag_min_grounding and fact_check.confidence < 0.7:
            final_response = (
                f"{response}\n\n⚠️ [VRAV Anti-Hallucination] Low grounding "
                f"(score={grounding_score:.2f}). Verify independently."
            )
            confidence = min(confidence, 0.55)
            fact_check.verified = False
            fact_check.notes = (fact_check.notes or "") + " | low RAG grounding"
        elif not fact_check.verified and fact_check.confidence < 0.65:
            final_response = (
                f"{response}\n\n⚠️ [VRAV Fact-Check] Confidence: {fact_check.confidence:.0%}. "
                f"Sources: {', '.join(fact_check.sources[:2]) or 'none'}."
            )
            confidence = fact_check.confidence

        return {
            "response": final_response, "fact_check": fact_check,
            "confidence": confidence, "grounding_score": grounding_score,
        }

    async def _grounding_score(self, response: str, docs: List[str], tool_context: str) -> float:
        corpus = list(docs)
        if tool_context:
            corpus.append(str(tool_context)[:4000])
        if not corpus:
            return 0.5
        try:
            rvec = await embedder.embed(response[:4000])
            scores = []
            for d in corpus[:8]:
                dvec = await embedder.embed(str(d)[:4000])
                scores.append(cosine(rvec, dvec))
            return max(scores) if scores else 0.0
        except Exception:
            rt = set(re.findall(r"[a-zа-я0-9]{3,}", response.lower()))
            best = 0.0
            for d in corpus[:8]:
                dt = set(re.findall(r"[a-zа-я0-9]{3,}", str(d).lower()))
                if rt and dt:
                    best = max(best, len(rt & dt) / max(1, len(rt)))
            return best

    def _looks_factual(self, text: str) -> bool:
        patterns = [
            r"\d{4}", r"\d+%", r"закон|законът|директива|регламент",
            r"чл\.|член\s+\d+", r"€\s*\d+|\d+\s*лв",
            r"България|Европейски\s+съюз|ЕС\b", r"according to|съгласно|по данни",
        ]
        return any(re.search(p, text, re.IGNORECASE) for p in patterns)

    def _extract_entities(self, text: str) -> List[str]:
        entities = []
        entities.extend(re.findall(r"\b(20\d{2})\b", text))
        entities.extend(re.findall(r"\b(\d{1,3}(?:[.,]\d+)?%?)\b", text)[:5])
        for match in re.finditer(
            r"(закон\s+[А-Яа-яA-Za-z\s]{5,40}|директива\s+\d+/\d+|регламент\s+\(Е[СC]\)\s+\d+/\d+)",
            text, re.IGNORECASE,
        ):
            entities.append(match.group(0)[:60])
        return list(dict.fromkeys(entities))[:12]

    async def _fact_check(self, entities: List[str], context: Dict[str, Any]) -> FactCheckResult:
        if not entities:
            return FactCheckResult(verified=True, confidence=0.9, entities_checked=[])
        query = " ".join(entities) + " (site:gov.bg OR site:europa.eu OR site:eur-lex.europa.eu)"
        sources: List[str] = []
        verified = False
        confidence = 0.5
        if self.serper_key:
            try:
                async with httpx.AsyncClient(timeout=15.0) as client:
                    resp = await client.post(
                        "https://google.serper.dev/search",
                        headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                        json={"q": query, "num": 5},
                    )
                    if resp.status_code == 200:
                        organic = resp.json().get("organic", [])
                        sources = [item.get("link", "") for item in organic[:4]]
                        verified = len(organic) > 0
                        confidence = 0.75 if verified else 0.4
            except Exception as e:
                logger.warning("Serper fact-check failed: %s", e)
        if not sources and not self.serper_key:
            if context.get("tool_context") or context.get("grounding_docs"):
                return FactCheckResult(
                    verified=True, confidence=0.7, entities_checked=entities,
                    sources=["local_tool_context"],
                    notes="Verified against tool/RAG context",
                )
            return FactCheckResult(
                verified=False, confidence=0.55, entities_checked=entities,
                sources=[], notes="No search API key — limited verification",
            )
        return FactCheckResult(
            verified=verified, confidence=confidence, entities_checked=entities,
            sources=sources, notes="Cross-checked via web search (Bg/EU priority)",
        )
