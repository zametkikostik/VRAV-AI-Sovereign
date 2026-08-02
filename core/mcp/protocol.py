"""MCP-compatible tool layer (JSON-RPC 2.0 tools/list + tools/call)."""

from __future__ import annotations

import inspect
import logging
from dataclasses import dataclass, field
from typing import Any, Awaitable, Callable, Dict, List, Optional, Union

from pydantic import BaseModel, Field

logger = logging.getLogger("vrav.mcp")
ToolHandler = Callable[..., Union[Any, Awaitable[Any]]]


class MCPToolSchema(BaseModel):
    name: str
    description: str
    inputSchema: Dict[str, Any] = Field(default_factory=lambda: {"type": "object", "properties": {}})


class JSONRPCRequest(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[str, int, None] = None
    method: str
    params: Optional[Dict[str, Any]] = None


class JSONRPCResponse(BaseModel):
    jsonrpc: str = "2.0"
    id: Union[str, int, None] = None
    result: Optional[Any] = None
    error: Optional[Dict[str, Any]] = None


@dataclass
class RegisteredTool:
    name: str
    description: str
    handler: ToolHandler
    input_schema: Dict[str, Any] = field(default_factory=dict)


class MCPToolRegistry:
    def __init__(self):
        self._tools: Dict[str, RegisteredTool] = {}

    def tool(self, name: Optional[str] = None, description: str = "",
             input_schema: Optional[Dict[str, Any]] = None):
        def deco(fn: ToolHandler):
            tool_name = name or fn.__name__
            schema = input_schema or self._infer_schema(fn)
            self._tools[tool_name] = RegisteredTool(
                name=tool_name,
                description=description or (fn.__doc__ or tool_name).strip().split("\n")[0],
                handler=fn,
                input_schema=schema,
            )
            return fn
        return deco

    def register(self, name: str, handler: ToolHandler, description: str = "",
                 input_schema: Optional[Dict[str, Any]] = None) -> None:
        self._tools[name] = RegisteredTool(
            name=name, description=description or name, handler=handler,
            input_schema=input_schema or {"type": "object", "properties": {}},
        )

    def list_tools(self) -> List[MCPToolSchema]:
        return [MCPToolSchema(name=t.name, description=t.description, inputSchema=t.input_schema)
                for t in self._tools.values()]

    async def call_tool(self, name: str, arguments: Optional[Dict[str, Any]] = None) -> Any:
        if name not in self._tools:
            raise KeyError(f"Unknown tool: {name}")
        tool = self._tools[name]
        result = tool.handler(**(arguments or {}))
        if inspect.isawaitable(result):
            result = await result
        return result

    async def handle_rpc(self, request: Dict[str, Any]) -> Dict[str, Any]:
        req_id = request.get("id")
        method = request.get("method") or ""
        params = request.get("params") or {}
        try:
            if method == "tools/list":
                tools = [t.model_dump() for t in self.list_tools()]
                return JSONRPCResponse(id=req_id, result={"tools": tools}).model_dump(exclude_none=True)
            if method == "tools/call":
                name = params.get("name")
                arguments = params.get("arguments") or {}
                result = await self.call_tool(name, arguments)
                content = [{"type": "text", "text": result if isinstance(result, str) else str(result)}]
                if isinstance(result, dict):
                    content = [{"type": "text", "text": str(result)}, {"type": "json", "json": result}]
                return JSONRPCResponse(id=req_id, result={"content": content, "isError": False}).model_dump(exclude_none=True)
            if method == "initialize":
                return JSONRPCResponse(id=req_id, result={
                    "protocolVersion": "2024-11-05",
                    "capabilities": {"tools": {}},
                    "serverInfo": {"name": "vrav-mcp", "version": "0.3.0"},
                }).model_dump(exclude_none=True)
            return JSONRPCResponse(id=req_id, error={"code": -32601, "message": f"Method not found: {method}"}).model_dump(exclude_none=True)
        except KeyError as e:
            return JSONRPCResponse(id=req_id, error={"code": -32001, "message": str(e)}).model_dump(exclude_none=True)
        except Exception as e:
            logger.exception("MCP call error")
            return JSONRPCResponse(id=req_id, error={"code": -32000, "message": str(e)}).model_dump(exclude_none=True)

    def _infer_schema(self, fn: ToolHandler) -> Dict[str, Any]:
        props: Dict[str, Any] = {}
        required: List[str] = []
        try:
            sig = inspect.signature(fn)
            for pname, param in sig.parameters.items():
                if pname in ("self", "cls"):
                    continue
                props[pname] = {"type": "string"}
                if param.default is inspect.Parameter.empty:
                    required.append(pname)
        except (TypeError, ValueError):
            pass
        schema: Dict[str, Any] = {"type": "object", "properties": props}
        if required:
            schema["required"] = required
        return schema

    def openai_tools_format(self) -> List[Dict[str, Any]]:
        out = []
        for t in self._tools.values():
            out.append({"type": "function", "function": {
                "name": t.name, "description": t.description, "parameters": t.input_schema,
            }})
        return out


mcp_registry = MCPToolRegistry()
