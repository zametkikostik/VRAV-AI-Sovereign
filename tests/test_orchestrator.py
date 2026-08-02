"""Basic orchestrator unit tests (mocked)."""

import pytest
from unittest.mock import AsyncMock, patch
from core.orchestrator import AgentOrchestrator
from core.models.schemas import StreamRequest


@pytest.mark.asyncio
async def test_detect_provider_bg():
    orch = AgentOrchestrator()
    provider, model = orch._detect_provider("Какъв е законът за ДДС в България?")
    assert provider == "ollama"
    assert "bggpt" in model.lower() or model == "bggpt"


@pytest.mark.asyncio
async def test_detect_provider_default():
    """Sovereign default: local Ollama (prefer_ollama=True)."""
    orch = AgentOrchestrator()
    provider, model = orch._detect_provider("Explain quantum computing")
    assert provider == "ollama"
    assert model  # non-empty model id


@pytest.mark.asyncio
async def test_execute_flow_mocked():
    orch = AgentOrchestrator()
    req = StreamRequest(prompt="Hello world, just a greeting")

    with patch.object(orch, "call_llm", new_callable=AsyncMock) as mock_llm:
        mock_llm.return_value = "Здравей! Аз съм VRAV AI."
        with patch.object(orch.guard, "validate_response", new_callable=AsyncMock) as mock_guard:
            mock_guard.return_value = {
                "response": "Здравей! Аз съм VRAV AI.",
                "fact_check": None,
                "confidence": 0.95,
            }
            result = await orch.execute(req)
            assert "VRAV" in result.response or "Здравей" in result.response
            assert result.confidence >= 0.9
