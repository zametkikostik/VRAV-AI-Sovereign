"""Optional LLM safety classifier via Ollama (Llama Guard–style)."""
from __future__ import annotations
import logging, re
from typing import Tuple
import httpx
from config.settings import settings
logger = logging.getLogger("vrav.safety.llm")
CLASSIFY_PROMPT = """Classify the user message as SAFE or UNSAFE.
UNSAFE: malware, exploits, weapons construction, fraud, CSAM, severe harm intent.
Otherwise SAFE (programming help, legal research, fiction without actionable crime).
Reply one line: SAFE  or  UNSAFE: reason

User message:
"""

class LLMSafetyClassifier:
    def __init__(self):
        self.enabled = bool(getattr(settings, "enable_llm_safety_classifier", False))
        self.model = getattr(settings, "safety_classifier_model", None) or "llama-guard3"
        self.ollama_url = settings.ollama_base_url
        self.fail_closed = bool(getattr(settings, "safety_classifier_fail_closed", False))

    async def check(self, text: str) -> Tuple[bool, str]:
        if not self.enabled:
            return True, "classifier_disabled"
        text = (text or "")[:6000]
        if not text.strip():
            return True, "empty"
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{self.ollama_url.rstrip('/')}/api/chat",
                    json={"model": self.model, "messages": [
                        {"role": "system", "content": "Safety classifier. Output SAFE or UNSAFE only."},
                        {"role": "user", "content": CLASSIFY_PROMPT + text},
                    ], "stream": False, "options": {"temperature": 0.0}},
                )
                if resp.status_code == 404:
                    return (False, "classifier_model_missing") if self.fail_closed else (True, "model_missing_fail_open")
                resp.raise_for_status()
                content = (resp.json().get("message") or {}).get("content") or ""
        except Exception as e:
            if self.fail_closed:
                return False, f"classifier_error:{e}"
            return True, "classifier_error_fail_open"
        upper = content.strip().upper()
        if upper.startswith("UNSAFE") or re.search(r"\bUNSAFE\b", upper):
            return False, content.strip().split("\n", 1)[0][:200]
        return True, "SAFE"

llm_safety = LLMSafetyClassifier()
