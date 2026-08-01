"""Streaming helpers — offline unit checks."""

from core.streaming.sse import sse_event


def test_sse_event_format():
    s = sse_event("token", {"text": "hello"})
    assert "event: token" in s
    assert "data:" in s
    assert "hello" in s


def test_sse_with_id():
    s = sse_event("done", {"ok": True}, event_id="1")
    assert "id: 1" in s
