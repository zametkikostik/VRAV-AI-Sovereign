"""LLM skill reviewer tests (heuristic path)."""
import pytest
from core.skills.llm_reviewer import LLMSkillReviewer

@pytest.mark.asyncio
async def test_reviewer_returns_structure():
    r = LLMSkillReviewer()
    # offline: may fall back to heuristic
    out = await r.review(
        prompt="How to file a GDPR DSAR?",
        response="1. Verify identity\n2. Collect data\n3. Respond in 30 days",
        meta={"fact_checked": True},
    )
    assert isinstance(out, dict)
