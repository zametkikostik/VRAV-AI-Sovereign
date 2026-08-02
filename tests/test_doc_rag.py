"""Document RAG indexer tests."""
from pathlib import Path
import pytest
from core.rag.doc_index import DocRAG, chunk_text

def test_chunk_text():
    chunks = chunk_text("a" * 2000, size=500, overlap=50)
    assert len(chunks) >= 3

@pytest.mark.asyncio
async def test_reindex_and_retrieve(tmp_path: Path):
    corpus = tmp_path / "corpus"
    corpus.mkdir()
    (corpus / "note.md").write_text(
        "GDPR CELEX 32016R0679. Срок за отговор един месец по чл. 12. КЗЛД е надзорният орган.",
        encoding="utf-8",
    )
    rag = DocRAG(corpus_dir=corpus, index_path=tmp_path / "doc_vectors.json", min_score=0.05, top_k=3)
    stats = await rag.reindex()
    assert stats["files"] == 1
    hits = await rag.retrieve("GDPR CELEX", top_k=3, min_score=0.0)
    assert hits

def test_list_files(tmp_path: Path):
    corpus = tmp_path / "c"
    corpus.mkdir()
    (corpus / "a.txt").write_text("hello", encoding="utf-8")
    rag = DocRAG(corpus_dir=corpus, index_path=tmp_path / "i.json")
    assert "a.txt" in rag.list_files()
