import pytest
from core.rag.embeddings import cosine, Embedder
from core.rag.skill_index import SkillRAG
from core.skills.manager import SkillManager
from pathlib import Path


def test_cosine_identical():
    v = [1.0, 0.0, 0.0]
    assert abs(cosine(v, v) - 1.0) < 1e-6


def test_hash_embed_stable():
    e = Embedder(dim=64)
    a = e._hash_embed("GDPR privacy law")
    b = e._hash_embed("GDPR privacy law")
    assert a == b
    assert abs(cosine(a, b) - 1.0) < 1e-6


@pytest.mark.asyncio
async def test_skill_rag_threshold(tmp_path: Path):
    mgr = SkillManager(root=tmp_path)
    (tmp_path / "gdpr_dsar.md").write_text(
        "# Skill: gdpr_dsar\nHandle data subject access requests under GDPR.\n",
        encoding="utf-8",
    )
    for _ in range(3):
        mgr.record_success(
            task_pattern="gdpr data subject access request workflow",
            steps=["verify identity", "collect data", "respond 30 days"],
            outcome="ok",
            tags=["legal"],
        )
    rag = SkillRAG(min_score=0.15, top_k=3)
    rag.index_path = tmp_path / "vectors.json"
    await rag.ensure_indexed(
        "gdpr_dsar",
        "GDPR data subject access request workflow verify identity respond",
    )
    hits = await rag.retrieve("How to process a GDPR DSAR request?", top_k=3, min_score=0.1)
    assert any(h["name"] == "gdpr_dsar" for h in hits)
