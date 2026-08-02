"""Orchestrator smoke tests (offline)."""
from core.models.schemas import StreamRequest

def test_stream_request_validation():
    r = StreamRequest(prompt="test prompt about GDPR")
    assert r.prompt.startswith("test")
    assert r.temperature == 0.7
