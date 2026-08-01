"""
Action Policy Gate — hard deny for harmful / destructive operations.

The agent may research and explain; it must never execute or produce
actionable steps for: malware, exploits, unauthorized access, violence,
self-harm methods, weapons construction, fraud, etc.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

READ_ONLY_TOOLS = {
    "echo",
    "eurlex_get",
    "cellar_search",
    "gdpr_article",
    "memory_list_facts",
    "skills_list",
    "web_search",
    "web_fetch",
    "wiki_summary",
    "memory_upsert_fact",
    "code_sandbox",
}

HARMFUL_PATTERNS = [
    r"(?i)\b(ransomware|malware|rootkit|keylogger|botnet)\b",
    r"(?i)\b(exploit\s+kit|zero[\s-]?day\s+exploit|buffer\s+overflow\s+payload)\b",
    r"(?i)\b(sql\s*injection\s+payload|xss\s+payload|reverse\s+shell)\b",
    r"(?i)\b(make\s+a\s+bomb|build\s+(a\s+)?(bomb|explosive|weapon))\b",
    r"(?i)\b(synthesize|produce)\s+(sarin|ricin|fentanyl|meth)\b",
    r"(?i)\b(how\s+to\s+(hack|breach|crack)\s+(into|password|account))\b",
    r"(?i)\b(credit\s+card\s+(dump|fraud|skimmer)|carding)\b",
    r"(?i)\b(child\s+sexual|csam|child\s+porn)\b",
    r"(?i)\brm\s+-rf\s+/\b",
    r"(?i)\b(ddos|denial[\s-]of[\s-]service)\s+(attack|tool)\b",
]

BLOCKED_HOST_FRAGMENTS = (
    "onion",
    "pastebin.com",
)


class PolicyGate:
    @classmethod
    def check_text(cls, text: str) -> Tuple[bool, str]:
        for p in HARMFUL_PATTERNS:
            if re.search(p, text or ""):
                return False, f"Blocked by safety policy (pattern match)"
        return True, "ok"

    @classmethod
    def check_tool_call(cls, name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        if name not in READ_ONLY_TOOLS and name not in {
            "memory_upsert_fact",
        }:
            if not name.startswith(("get_", "list_", "search_", "fetch_", "wiki_")):
                pass

        blob = name + " " + str(arguments)
        ok, reason = cls.check_text(blob)
        if not ok:
            return False, reason

        if name == "web_fetch":
            url = str(arguments.get("url") or "")
            if not url.startswith(("http://", "https://")):
                return False, "Only http(s) URLs allowed"
            lower = url.lower()
            for frag in BLOCKED_HOST_FRAGMENTS:
                if frag in lower and "wikipedia" not in lower:
                    if frag == "onion":
                        return False, "Tor/onion URLs blocked"
        return True, "ok"

    @classmethod
    def sanitize_research_query(cls, query: str) -> str:
        ok, _ = cls.check_text(query)
        if not ok:
            raise PermissionError("Research query blocked by safety policy")
        return query.strip()[:300]


policy_gate = PolicyGate()
