"""SSE Streaming helpers for VRAV orchestrator."""

from __future__ import annotations

import json
from typing import Any, AsyncIterator, Optional


def sse_event(event: str, data: Any, event_id: Optional[str] = None) -> str:
    payload = data if isinstance(data, str) else json.dumps(data, ensure_ascii=False)
    lines = []
    if event_id:
        lines.append(f"id: {event_id}")
    lines.append(f"event: {event}")
    for line in payload.splitlines() or [payload]:
        lines.append(f"data: {line}")
    lines.append("")
    return "\n".join(lines) + "\n"


async def stream_tokens_from_text(text: str, chunk_size: int = 24) -> AsyncIterator[str]:
    for i in range(0, len(text), chunk_size):
        yield text[i : i + chunk_size]
