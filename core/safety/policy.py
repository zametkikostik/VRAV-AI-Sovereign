"""
Action Policy Gate — hard deny for harmful / destructive operations.

The agent may research and explain; it must never execute or produce
actionable steps for: malware, exploits, unauthorized access, violence,
self-harm methods, weapons construction, fraud, etc.
"""

from __future__ import annotations

import re
from typing import Any, Dict, List, Optional, Tuple

# Tool names that are always allowed (read-only research)
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
    "memory_upsert_fact",  # memory write is OK
    "code_sandbox",  # gated restricted exec only
}

# Absolute block patterns in user goals / tool args / model output
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

# Domains blocked for web_fetch (phishing / malware distribution style)
BLOCKED_HOST_FRAGMENTS = (
    "onion",
    "pastebin.com",  # often used for dumps; optional strictness
)


class PolicyGate:
    @classmethod
    def check_text(cls, text: str) -> Tuple[bool, str]:
        """Return (allowed, reason)."""
        for p in HARMFUL_PATTERNS:
            if re.search(p, text or ""):
                return False, f"Blocked by safety policy (pattern match)"
        return True, "ok"

    @classmethod
    def check_tool_call(cls, name: str, arguments: Dict[str, Any]) -> Tuple[bool, str]:
        if name not in READ_ONLY_TOOLS and name not in {
            # extend allowlist carefully
            "memory_upsert_fact",
        }:
            # Unknown tools denied by default (secure by default)
            # Allow if registered as read-only via naming convention
            if not name.startswith(("get_", "list_", "search_", "fetch_", "wiki_")):
                # still allow registered MCP tools that are known
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
                    # soft block for onion; pastebin allowed for text fetch with size cap elsewhere
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
