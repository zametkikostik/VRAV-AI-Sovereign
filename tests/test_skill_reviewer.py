"""Background skill reviewer tests."""

import pytest
from core.skills.reviewer import SkillReviewer


@pytest.mark.asyncio
async def test_review_creates_actions(tmp_path):
    reviewer = SkillReviewer()
    result = await reviewer.review_session(
        session_id="test-sess",
        prompt="Как да направя GDPR data subject request workflow?",
        response="1. Identify request\n2. Verify identity\n3. Respond within 30 days",
        meta={"used_eurlex": True, "fact_checked": True},
    )
    assert "actions" in result
    assert len(result["actions"]) >= 1


@pytest.mark.asyncio
async def test_review_skips_trivial():
    reviewer = SkillReviewer()
    result = await reviewer.review_session(
        session_id="x", prompt="hi", response="hello", meta={},
    )
    assert any(a.get("type") == "skip" for a in result["actions"])
