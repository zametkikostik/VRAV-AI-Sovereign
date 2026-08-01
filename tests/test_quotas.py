from pathlib import Path
from core.sandbox.quotas import QuotaManager
from core.sandbox.runner import CodeSandbox


def test_quota_allows_then_records(tmp_path: Path):
    qm = QuotaManager(db_path=tmp_path / "q.db")
    st = qm.check("u1", 100)
    assert st["allowed"] is True
    qm.record("u1", 10.0, 100, True)
    st2 = qm.check("u1", 100)
    assert st2["used_runs"] >= 1


def test_sandbox_with_user():
    r = CodeSandbox().run("print(1+1)", user_id="testuser")
    assert r["ok"] is True
    assert "quota" in r
