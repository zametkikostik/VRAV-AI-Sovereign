"""Tests for Anti-Hallucination Guard."""

import pytest
from core.safety.guard import AntiHallucinationGuard


@pytest.mark.asyncio
async def test_non_factual_skips_search():
    guard = AntiHallucinationGuard()
    result = await guard.validate_response("Здравей! Как си днес?", {"prompt": "hello"})
    assert result["confidence"] >= 0.9
    assert result["fact_check"].verified is True


@pytest.mark.asyncio
async def test_entity_extraction():
    guard = AntiHallucinationGuard()
    entities = guard._extract_entities("През 2023 година БВП нарасна с 1.8%.")
    assert "2023" in entities or any("1.8" in e for e in entities)


def test_looks_factual():
    guard = AntiHallucinationGuard()
    assert guard._looks_factual("Според закон чл. 15 от 2021")
    assert not guard._looks_factual("Просто поздрав")
