"""CELLAR SPARQL client — precise EU legal document search."""

from __future__ import annotations

import logging
import re
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger("vrav.cellar")
SPARQL_ENDPOINT = "https://publications.europa.eu/webapi/rdf/sparql"


class CellarSPARQL:
    def __init__(self, endpoint: str = SPARQL_ENDPOINT, language: str = "eng"):
        self.endpoint = endpoint
        self.language = language

    async def search(self, query: str, max_results: int = 5, work_type: Optional[str] = None) -> List[Dict[str, Any]]:
        q = query.replace('"', " ").replace("\\", " ")[:120]
        type_filter = ""
        if work_type:
            type_filter = f'FILTER(CONTAINS(LCASE(STR(?id)), "{work_type.lower()}"))'
        sparql = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?id ?title WHERE {{
  ?work cdm:work_id ?id .
  OPTIONAL {{
    ?exp cdm:expression_belongs_to_work ?work .
    ?exp cdm:expression_title ?title .
    FILTER(LANG(?title) = "{self.language}" || LANG(?title) = "")
  }}
  FILTER(
    CONTAINS(LCASE(STR(?id)), LCASE("{q}")) ||
    CONTAINS(LCASE(STR(?title)), LCASE("{q}"))
  )
  {type_filter}
}}
LIMIT {int(max_results)}
"""
        return await self._query(sparql)

    async def by_celex(self, celex: str) -> List[Dict[str, Any]]:
        celex = celex.strip().upper()
        sparql = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?id ?title WHERE {{
  ?work cdm:work_id ?id .
  FILTER(CONTAINS(STR(?id), "{celex}"))
  OPTIONAL {{
    ?exp cdm:expression_belongs_to_work ?work .
    ?exp cdm:expression_title ?title .
  }}
}}
LIMIT 5
"""
        return await self._query(sparql)

    async def recent_regulations(self, year: int = 2024, limit: int = 5) -> List[Dict[str, Any]]:
        sparql = f"""
PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>
SELECT DISTINCT ?work ?id ?title WHERE {{
  ?work cdm:work_id ?id .
  FILTER(CONTAINS(STR(?id), "{year}") && CONTAINS(STR(?id), "R"))
  OPTIONAL {{
    ?exp cdm:expression_belongs_to_work ?work .
    ?exp cdm:expression_title ?title .
    FILTER(LANG(?title) = "eng" || LANG(?title) = "")
  }}
}}
LIMIT {int(limit)}
"""
        return await self._query(sparql)

    async def _query(self, sparql: str) -> List[Dict[str, Any]]:
        headers = {
            "Accept": "application/sparql-results+json",
            "User-Agent": "VRAV-AI/0.2 (research; +https://vrav.ai)",
        }
        params = {"query": sparql, "format": "application/sparql-results+json"}
        try:
            async with httpx.AsyncClient(timeout=40.0) as client:
                resp = await client.get(self.endpoint, params=params, headers=headers)
                if resp.status_code != 200:
                    resp = await client.post(
                        self.endpoint, data={"query": sparql},
                        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
                    )
                if resp.status_code != 200:
                    return [{"error": f"HTTP {resp.status_code}", "detail": resp.text[:300]}]
                data = resp.json()
                bindings = data.get("results", {}).get("bindings", [])
                out: List[Dict[str, Any]] = []
                for b in bindings:
                    item = {k: v.get("value") for k, v in b.items()}
                    wid = item.get("id") or ""
                    m = re.search(r"([0-9]{5}[A-Z][0-9]{4})", wid)
                    if m:
                        item["celex"] = m.group(1)
                    out.append(item)
                return out
        except Exception as e:
            logger.exception("CELLAR SPARQL failed")
            return [{"error": str(e)}]


cellar = CellarSPARQL(language="eng")
