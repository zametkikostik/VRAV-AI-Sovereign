"""
True token streaming from Ollama (stream: true) and OpenRouter SSE.
"""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator, Dict, List, Optional

import httpx

from config.settings import settings

logger = logging.getLogger("vrav.stream")


async def stream_ollama(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
    base_url: Optional[str] = None,
) -> AsyncIterator[str]:
    url = f"{(base_url or settings.ollama_base_url).rstrip('/')}/api/chat"
    payload = {
        "model": model,
        "messages": messages,
        "stream": True,
        "options": {"temperature": temperature},
    }
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json=payload) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                try:
                    data = json.loads(line)
                except json.JSONDecodeError:
                    continue
                msg = data.get("message") or {}
                chunk = msg.get("content") or ""
                if chunk:
                    yield chunk
                if data.get("done"):
                    break


async def stream_openrouter(
    messages: List[Dict[str, str]],
    model: str,
    temperature: float = 0.7,
) -> AsyncIterator[str]:
    if not settings.openrouter_api_key:
        raise RuntimeError("OpenRouter API key not configured")

    url = f"{settings.openrouter_base_url.rstrip('/')}/chat/completions"
    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "HTTP-Referer": "https://vrav.ai",
        "X-Title": "VRAV AI Sovereign Orchestrator",
        "Content-Type": "application/json",
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "stream": True,
    }
    async with httpx.AsyncClient(timeout=None) as client:
        async with client.stream("POST", url, json=payload, headers=headers) as resp:
            resp.raise_for_status()
            async for line in resp.aiter_lines():
                if not line:
                    continue
                if line.startswith(":"):
                    continue
                if not line.startswith("data:"):
                    continue
                data_str = line[5:].strip()
                if data_str == "[DONE]":
                    break
                try:
                    data = json.loads(data_str)
                except json.JSONDecodeError:
                    continue
                choices = data.get("choices") or []
                if not choices:
                    continue
                delta = choices[0].get("delta") or {}
                chunk = delta.get("content") or ""
                if chunk:
                    yield chunk


async def stream_llm(
    messages: List[Dict[str, str]],
    provider: str,
    model: str,
    temperature: float = 0.7,
) -> AsyncIterator[str]:
    if provider == "ollama":
        async for chunk in stream_ollama(messages, model, temperature):
            yield chunk
    else:
        async for chunk in stream_openrouter(messages, model, temperature):
            yield chunk
