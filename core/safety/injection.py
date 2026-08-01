"""Hardened Prompt Injection Shield — multi-layer."""

from __future__ import annotations

import base64
import logging
import re
from typing import List, Tuple

from fastapi import HTTPException
from config.settings import settings

logger = logging.getLogger("vrav.injection")


class InjectionGuard:
    BLOCK_PATTERNS: List[str] = [
        r"(?i)ignore\s+(all\s+)?(previous|prior|above|earlier)\s+(instructions?|rules?|prompts?)",
        r"(?i)disregard\s+(all\s+)?(previous|prior|system)\s+",
        r"(?i)forget\s+(everything|all|your)\s+(instructions?|rules?|training)",
        r"(?i)dan\s+mode|developer\s+mode|jailbreak\s+mode",
        r"(?i)you\s+are\s+now\s+(a|an|the)\s+(unrestricted|evil|uncensored)",
        r"(?i)system\s+prompt\s*(:|=|is)",
        r"(?i)override\s+(system|safety|alignment|policy)",
        r"(?i)pretend\s+you\s+(have\s+no|are\s+without)\s+restrictions",
        r"(?i)act\s+as\s+if\s+you\s+(are\s+)?unrestricted",
        r"(?i)do\s+not\s+follow\s+(your|the)\s+(safety|system)\s+",
        r"(?i)new\s+instructions?\s*:\s*you\s+must",
        r"(?i)<\s*/?\s*system\s*>",
        r"(?i)\[\s*system\s*\]",
        r"(?i)BEGIN\s+SYSTEM\s+PROMPT|END\s+SYSTEM\s+PROMPT",
        r"(?i)reveal\s+(your|the)\s+(system\s+)?prompt",
        r"(?i)print\s+(your|the)\s+hidden\s+instructions?",
    ]
    ROLE_CONFUSION = [
        r"(?i)from\s+now\s+on\s+you\s+are",
        r"(?i)your\s+new\s+persona\s+is",
        r"(?i)enter\s+character\s*:",
        r"(?i)sudo\s+mode",
        r"(?i)admin\s+override",
    ]

    @classmethod
    def check(cls, prompt: str) -> str:
        if not settings.enable_prompt_injection_shield:
            return prompt
        if len(prompt) > settings.max_prompt_length:
            raise HTTPException(status_code=413, detail="Prompt too long")
        for pattern in cls.BLOCK_PATTERNS + cls.ROLE_CONFUSION:
            if re.search(pattern, prompt):
                logger.warning("Injection blocked by pattern: %s", pattern[:40])
                raise HTTPException(status_code=403, detail="Обнаружена попытка prompt injection. Запрос отклонён.")
        if cls._suspicious_encoding(prompt):
            raise HTTPException(status_code=403, detail="Подозрительная обфускация промпта")
        if cls._smuggle_score(prompt) >= 4:
            raise HTTPException(status_code=403, detail="Обнаружены признаки instruction smuggling")
        return prompt

    @classmethod
    def _suspicious_encoding(cls, text: str) -> bool:
        b64_blobs = re.findall(r"[A-Za-z0-9+/]{80,}={0,2}", text)
        for blob in b64_blobs:
            try:
                decoded = base64.b64decode(blob + "==").decode("utf-8", errors="ignore").lower()
                if any(k in decoded for k in ("ignore", "system", "jailbreak", "override")):
                    return True
            except Exception:
                pass
        if len(text) > 100:
            special = sum(1 for c in text if c in "{}[]<>|\\^~`")
            if special / len(text) > 0.15:
                return True
        return False

    @classmethod
    def _smuggle_score(cls, text: str) -> int:
        signals = [
            r"(?i)instruction", r"(?i)system", r"(?i)override", r"(?i)ignore",
            r"(?i)hidden", r"(?i)confidential\s+prompt", r"(?i)###\s*system", r"(?i)---\s*system",
        ]
        return sum(1 for p in signals if re.search(p, text))

    @classmethod
    def sanitize_output_canary(cls, output: str) -> Tuple[str, bool]:
        leak_patterns = [
            r"(?i)my\s+system\s+prompt\s+is",
            r"(?i)the\s+hidden\s+instructions?\s+(are|were)",
            r"(?i)VRAV\s+internal\s+policy",
        ]
        for p in leak_patterns:
            if re.search(p, output):
                return "[Ответ заблокирован: обнаружена утечка системного контекста]", True
        return output, False
