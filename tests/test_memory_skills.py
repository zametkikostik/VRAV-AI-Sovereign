from pathlib import Path
from core.memory.store import MemoryStore
from core.skills.manager import SkillManager

def test_memory_facts(tmp_path: Path):
    ms = MemoryStore(db_path=tmp_path / "m.db", md_path=tmp_path / "MEMORY.md")
    sid = ms.create_session("t")
    ms.add_turn(sid, "user", "hello")
    ms.upsert_fact("lang", "bg")
    assert ms.get_fact("lang") == "bg"
    facts = ms.get_facts()
    assert any(f["key"] == "lang" for f in facts)

def test_skill_distill(tmp_path: Path):
    sm = SkillManager(root=tmp_path)
    for _ in range(3):
        sm.record_success("gdpr dsar flow", ["verify", "collect", "reply"], "ok", tags=["legal"])
    skills = sm.list_skills()
    assert skills
