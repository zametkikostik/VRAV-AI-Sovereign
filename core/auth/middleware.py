"""Auth middleware. AUTH_MODE=off|optional|required"""
from __future__ import annotations
import os
from typing import Optional
from fastapi import Header, HTTPException, Request
from starlette.middleware.base import BaseHTTPMiddleware
from core.auth.store import auth_store

AUTH_MODE = os.getenv("AUTH_MODE", "off").lower()
PUBLIC = ("/api/health", "/docs", "/openapi.json", "/redoc", "/static", "/", "/app", "/ui")

async def get_current_user(request: Request, authorization: Optional[str] = Header(default=None),
                           x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")):
    key = x_api_key or authorization or request.headers.get("X-API-Key") or request.query_params.get("api_key")
    if not key:
        if AUTH_MODE == "required":
            raise HTTPException(401, "API key required")
        return None
    user = auth_store.resolve_key(key)
    if not user and AUTH_MODE in ("required", "optional"):
        raise HTTPException(401, "Invalid API key")
    if user:
        request.state.user = user
    return user

class AuthMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        path = request.url.path
        if AUTH_MODE != "required":
            return await call_next(request)
        if path in ("/", "/app", "/ui", "/docs", "/openapi.json", "/redoc", "/api/health") or path.startswith("/static") or path.startswith("/ui/"):
            return await call_next(request)
        if not path.startswith("/api"):
            return await call_next(request)
        key = request.headers.get("Authorization") or request.headers.get("X-API-Key")
        user = auth_store.resolve_key(key or "")
        if not user:
            from fastapi.responses import JSONResponse
            return JSONResponse({"detail": "API key required"}, status_code=401)
        request.state.user = user
        return await call_next(request)
