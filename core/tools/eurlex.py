"""EUR-Lex integration — public CELEX HTML + search (read-only)."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote

import httpx

logger = logging.getLogger("vrav.eurlex")
CELEX_HTML = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/HTML/?uri=CELEX:{celex}"
CELEX_TXT = "https://eur-lex.europa.eu/legal-content/{lang}/TXT/?uri=CELEX:{celex}"


class EURLexClient:
    def __init__(self, language: str = "bg"):
        self.language = language if language in ("bg", "en", "de", "fr", "es", "it", "pl", "ro") else "en"

    async def get_by_celex(self, celex: str, language: Optional[str] = None) -> Dict[str, Any]:
        celex = celex.strip().upper().replace(" ", "")
        if not re.match(r"^[0-9A-Z()]+$", celex):
            return {"error": "Invalid CELEX format", "celex": celex}
        lang = language or self.language
        url = CELEX_HTML.format(lang=lang.upper(), celex=celex)
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "VRAV-AI/0.1 (research)"})
            if resp.status_code != 200:
                if lang != "en":
                    return await self.get_by_celex(celex, language="en")
                return {"error": f"HTTP {resp.status_code}", "celex": celex, "url": url}
            html = resp.text
            text = self._html_to_text(html)
            return {
                "celex": celex, "title": self._extract_title(html) or celex,
                "language": lang, "url": url, "text": text[:50000], "length": len(text),
            }

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        q = quote(query)
        search_url = f"https://eur-lex.europa.eu/search.html?scope=EURLEX&type=quick&lang={self.language}&text={q}"
        results: List[Dict[str, Any]] = []
        try:
            async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
                resp = await client.get(search_url, headers={"User-Agent": "VRAV-AI/0.1 (research)"})
                if resp.status_code != 200:
                    return [{"error": f"search HTTP {resp.status_code}", "query": query}]
                html = resp.text
                celexes = re.findall(r"CELEX[:\s]*([0-9]{5}[A-Z][0-9]{4})", html, re.I)
                titles = re.findall(r'title="([^"]{10,120})"', html)
                seen = set()
                for i, c in enumerate(celexes):
                    c = c.upper()
                    if c in seen:
                        continue
                    seen.add(c)
                    results.append({
                        "celex": c, "title": titles[i] if i < len(titles) else c,
                        "url": CELEX_TXT.format(lang=self.language.upper(), celex=c),
                    })
                    if len(results) >= max_results:
                        break
        except Exception as e:
            return [{"error": str(e), "query": query}]
        if not results:
            results.append({"note": "No CELEX extracted", "query": query, "search_url": search_url})
        return results

    async def get_gdpr_article(self, article: int) -> Dict[str, Any]:
        doc = await self.get_by_celex("32016R0679", language="en")
        if "error" in doc:
            return doc
        text = doc.get("text", "")
        pattern = rf"(Article\s+{article}\b[\s\S]*?)(?=Article\s+{article + 1}\b|$)"
        m = re.search(pattern, text, re.I)
        return {
            "celex": "32016R0679", "article": article, "title": doc.get("title"),
            "excerpt": (m.group(1).strip()[:8000] if m else "Article not found"),
            "url": doc.get("url"),
        }

    def _html_to_text(self, html: str) -> str:
        text = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        text = re.sub(r"(?is)<style.*?>.*?</style>", " ", text)
        text = re.sub(r"(?is)<[^>]+>", " ", text)
        text = re.sub(r"&nbsp;", " ", text)
        text = re.sub(r"&amp;", "&", text)
        text = re.sub(r"&lt;", "<", text)
        text = re.sub(r"&gt;", ">", text)
        text = re.sub(r"\s+", " ", text)
        return text.strip()

    def _extract_title(self, html: str) -> Optional[str]:
        m = re.search(r"<title>([^<]+)</title>", html, re.I)
        if m:
            return m.group(1).strip()
        m = re.search(r'<meta\s+property="og:title"\s+content="([^"]+)"', html, re.I)
        return m.group(1).strip() if m else None


eurlex_client = EURLexClient(language="bg")
