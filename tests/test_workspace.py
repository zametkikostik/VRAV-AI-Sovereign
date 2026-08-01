"""OpenClaw-style workspace tests."""

from pathlib import Path
from core.workspace.bootstrap import Workspace


def test_workspace_defaults(tmp_path: Path):
    ws = Workspace(root=tmp_path)
    files = ws.list_files()
    assert "SOUL.md" in files
    assert "AGENTS.md" in files
    assert "IDENTITY.md" in files
    soul = ws.read("SOUL.md")
    assert "VRAV" in soul
    block = ws.build_injection_block()
    assert "SOUL.md" in block
    assert ws.bootstrap_pending() is True
    assert ws.complete_bootstrap() is True
    assert ws.bootstrap_pending() is False


def test_workspace_write(tmp_path: Path):
    ws = Workspace(root=tmp_path)
    ws.write("USER.md", "# USER\nlang: bg\n")
    assert "bg" in ws.read("USER.md")
