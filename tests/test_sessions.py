from pathlib import Path
from core.sessions.store import SessionStore


def test_session_lifecycle(tmp_path: Path):
    store = SessionStore(db_path=tmp_path / "s.db")
    sid = store.create(title="test", agents=["research", "critic"])
    store.add_turn(sid, "user", "user", "hello")
    store.add_turn(sid, "research", "assistant", "hi")
    store.update_blackboard(sid, {"notes": ["n1"], "goal": "g"})
    sess = store.get(sid)
    assert sess["title"] == "test"
    assert "research" in sess["agents"]
    assert sess["blackboard"]["goal"] == "g"
    turns = store.get_turns(sid)
    assert len(turns) == 2
    store.close(sid)
    assert store.get(sid)["status"] == "closed"
