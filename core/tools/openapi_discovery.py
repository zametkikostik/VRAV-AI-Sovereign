"""OpenAPI / Swagger Discovery — turn third-party schemas into agent tools."""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import httpx
import yaml

from core.models.schemas import OpenAPITool

logger = logging.getLogger("vrav.tools.openapi")


class OpenAPIDiscovery:
    def __init__(self):
        self.registry: Dict[str, OpenAPITool] = {}

    async def discover(self, schema_url: str, base_url: Optional[str] = None) -> List[OpenAPITool]:
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.get(schema_url)
            resp.raise_for_status()
            content_type = resp.headers.get("content-type", "")
            text = resp.text
            if "yaml" in content_type or schema_url.endswith((".yaml", ".yml")):
                schema = yaml.safe_load(text)
            else:
                schema = resp.json()
        return self._parse_schema(schema, base_url or self._infer_base(schema, schema_url))

    def _infer_base(self, schema: Dict, schema_url: str) -> str:
        servers = schema.get("servers") or []
        if servers and isinstance(servers[0], dict) and "url" in servers[0]:
            return servers[0]["url"].rstrip("/")
        host = schema.get("host")
        base_path = schema.get("basePath", "")
        schemes = schema.get("schemes", ["https"])
        if host:
            return f"{schemes[0]}://{host}{base_path}".rstrip("/")
        return schema_url.rsplit("/", 1)[0]

    def _parse_schema(self, schema: Dict[str, Any], base_url: str) -> List[OpenAPITool]:
        tools: List[OpenAPITool] = []
        paths = schema.get("paths") or {}
        for path, methods in paths.items():
            if not isinstance(methods, dict):
                continue
            for method, op in methods.items():
                if method.lower() not in ("get", "post", "put", "patch", "delete"):
                    continue
                if not isinstance(op, dict):
                    continue
                op_id = op.get("operationId") or f"{method}_{path.replace('/', '_').strip('_')}"
                name = op_id.replace(" ", "_").lower()
                description = op.get("summary") or op.get("description") or name
                parameters: Dict[str, Any] = {}
                for p in op.get("parameters") or []:
                    if isinstance(p, dict) and "name" in p:
                        parameters[p["name"]] = {
                            "in": p.get("in", "query"),
                            "required": p.get("required", False),
                            "schema": p.get("schema") or {"type": p.get("type", "string")},
                        }
                if "requestBody" in op:
                    parameters["body"] = {
                        "in": "body",
                        "required": op["requestBody"].get("required", False),
                        "schema": op["requestBody"].get("content", {}).get("application/json", {}).get("schema", {}),
                    }
                tool = OpenAPITool(
                    name=name, description=description[:300], method=method.upper(),
                    path=path, parameters=parameters, base_url=base_url,
                )
                self.registry[name] = tool
                tools.append(tool)
        return tools

    def list_tools(self) -> List[OpenAPITool]:
        return list(self.registry.values())

    async def call(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        tool = self.registry.get(name)
        if not tool:
            return {"error": f"Unknown tool: {name}"}
        args = arguments or {}
        url = tool.base_url.rstrip("/") + tool.path
        for k, meta in tool.parameters.items():
            if meta.get("in") == "path" and k in args:
                url = url.replace("{" + k + "}", str(args[k]))
        params = {k: v for k, v in args.items()
                  if tool.parameters.get(k, {}).get("in") == "query"}
        body = args.get("body") if "body" in tool.parameters else None
        async with httpx.AsyncClient(timeout=30.0, follow_redirects=True) as client:
            resp = await client.request(tool.method, url, params=params, json=body)
            try:
                data = resp.json()
            except Exception:
                data = {"text": resp.text[:5000]}
            return {"status": resp.status_code, "data": data}


openapi_discovery = OpenAPIDiscovery()
