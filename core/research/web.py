"""Safe web research: DuckDuckGo/Serper search, fetch, Wikipedia."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional
from urllib.parse import quote_plus, urlparse, unquote

import httpx

from config.settings import settings
from core.safety.policy import policy_gate

logger = logging.getLogger("vrav.research")
MAX_FETCH_BYTES = 500_000
MAX_TEXT_CHARS = 12_000
BLOCKED_IP_PREFIXES = ("127.", "10.", "192.168.", "169.254.", "0.", "localhost")


def _is_safe_url(url: str) -> bool:
    try:
        p = urlparse(url)
    except Exception:
        return False
    if p.scheme not in ("http", "https"):
        return False
    host = (p.hostname or "").lower()
    if not host or host == "localhost":
        return False
    for pref in BLOCKED_IP_PREFIXES:
        if host.startswith(pref):
            return False
    return True


class WebResearch:
    def __init__(self):
        self.serper_key = settings.serper_api_key

    async def search(self, query: str, max_results: int = 5) -> List[Dict[str, Any]]:
        query = policy_gate.sanitize_research_query(query)
        if self.serper_key:
            try:
                return await self._search_serper(query, max_results)
            except Exception as e:
                logger.warning("Serper failed: %s", e)
        return await self._search_ddg(query, max_results)

    async def _search_serper(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        async with httpx.AsyncClient(timeout=20.0) as client:
            resp = await client.post(
                "https://google.serper.dev/search",
                headers={"X-API-KEY": self.serper_key, "Content-Type": "application/json"},
                json={"q": query, "num": max_results},
            )
            resp.raise_for_status()
            data = resp.json()
            return [{"title": i.get("title"), "url": i.get("link"), "snippet": i.get("snippet")}
                    for i in data.get("organic", [])[:max_results]]

    async def _search_ddg(self, query: str, max_results: int) -> List[Dict[str, Any]]:
        url = f"https://html.duckduckgo.com/html/?q={quote_plus(query)}"
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "VRAV-AI/0.5 (research)"})
            if resp.status_code != 200:
                return [{"error": f"search HTTP {resp.status_code}", "query": query}]
            html = resp.text
            results: List[Dict[str, Any]] = []
            for m in re.finditer(r'class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>', html, re.I | re.S):
                href, title = m.group(1), re.sub(r"<[^>]+>", "", m.group(2))
                title = re.sub(r"\s+", " ", title).strip()
                if "uddg=" in href:
                    um = re.search(r"uddg=([^&]+)", href)
                    if um:
                        href = unquote(um.group(1))
                if not _is_safe_url(href):
                    continue
                results.append({"title": title, "url": href, "snippet": ""})
                if len(results) >= max_results:
                    break
            return results or [{"note": "no results", "query": query}]

    async def fetch(self, url: str) -> Dict[str, Any]:
        if not _is_safe_url(url):
            return {"error": "URL blocked by safety policy", "url": url}
        async with httpx.AsyncClient(timeout=25.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": "VRAV-AI/0.5 (research)"})
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}", "url": url}
            content_type = resp.headers.get("content-type", "")
            if "text" not in content_type and "json" not in content_type and "xml" not in content_type:
                return {"error": f"Non-text content-type: {content_type}", "url": url}
            raw = resp.content[:MAX_FETCH_BYTES]
            html = raw.decode(resp.encoding or "utf-8", errors="replace")
            text = self._html_to_text(html)[:MAX_TEXT_CHARS]
            return {"url": str(resp.url), "title": self._title(html), "text": text, "length": len(text)}

    async def wiki_summary(self, title: str, lang: str = "en") -> Dict[str, Any]:
        title = policy_gate.sanitize_research_query(title)
        lang = lang if re.match(r"^[a-z]{2}$", lang or "") else "en"
        api = f"https://{lang}.wikipedia.org/api/rest_v1/page/summary/{quote_plus(title)}"
        async with httpx.AsyncClient(timeout=20.0, follow_redirects=True) as client:
            resp = await client.get(api, headers={"User-Agent": "VRAV-AI/0.5"})
            if resp.status_code != 200:
                return {"error": f"HTTP {resp.status_code}", "title": title}
            data = resp.json()
            return {
                "title": data.get("title"), "description": data.get("description"),
                "extract": data.get("extract"),
                "url": data.get("content_urls", {}).get("desktop", {}).get("page"),
            }

    def _html_to_text(self, html: str) -> str:
        html = re.sub(r"(?is)<script.*?>.*?</script>", " ", html)
        html = re.sub(r"(?is)<style.*?>.*?</style>", " ", html)
        html = re.sub(r"(?is)<[^>]+>", " ", html)
        html = re.sub(r"&nbsp;", " ", html)
        html = re.sub(r"&amp;", "&", html)
        html = re.sub(r"\s+", " ", html)
        return html.strip()

    def _title(self, html: str) -> str:
        m = re.search(r"<title>([^<]+)</title>", html, re.I)
        return m.group(1).strip() if m else ""


web_research = WebResearch()
