"""OpenClaw-style workspace bootstrap files."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional

logger = logging.getLogger("vrav.workspace")
WORKSPACE_DIR = Path(__file__).resolve().parents[2] / "data" / "workspace"

DEFAULTS: Dict[str, str] = {
    "SOUL.md": "# SOUL — VRAV AI\n\n## Identity\nYou are VRAV AI — a sovereign, privacy-first agentic assistant for Bulgaria and the EU.\n",
    "AGENTS.md": "# AGENTS — Operating Instructions\n\n## Core loop\n1. Understand intent\n2. Pull memory + skills + tools when relevant\n3. Answer with sources and confidence\n",
    "IDENTITY.md": "# IDENTITY\n\n- Name: VRAV AI\n- Role: Sovereign Agentic Orchestrator\n- Emoji: 🛡️\n",
    "USER.md": "# USER\n\n## Profile\n- (filled by agent as facts are learned)\n",
    "BOOTSTRAP.md": "# BOOTSTRAP — first run\n\nOn first interaction greet briefly. This file is removed after first session.\n",
}


class Workspace:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or WORKSPACE_DIR
        self.root.mkdir(parents=True, exist_ok=True)
        self._ensure_defaults()

    def _ensure_defaults(self) -> None:
        for name, content in DEFAULTS.items():
            path = self.root / name
            if not path.exists():
                try:
                    path.write_text(content, encoding="utf-8")
                except OSError as e:
                    logger.warning("Cannot write %s: %s", name, e)

    def read(self, name: str) -> str:
        path = self.root / name
        if not path.exists():
            return ""
        try:
            return path.read_text(encoding="utf-8")
        except OSError:
            return ""

    def write(self, name: str, content: str) -> None:
        (self.root / name).write_text(content, encoding="utf-8")

    def list_files(self) -> List[str]:
        return sorted(p.name for p in self.root.glob("*.md"))

    def build_injection_block(self, max_chars: int = 6000) -> str:
        parts: List[str] = []
        for name in ("SOUL.md", "AGENTS.md", "IDENTITY.md", "USER.md"):
            text = self.read(name).strip()
            if text:
                parts.append(f"### {name}\n{text}")
        block = "\n\n".join(parts)
        if len(block) > max_chars:
            block = block[:max_chars] + "\n…[truncated]"
        return block

    def complete_bootstrap(self) -> bool:
        path = self.root / "BOOTSTRAP.md"
        if path.exists():
            try:
                path.unlink()
                return True
            except OSError:
                return False
        return False

    def bootstrap_pending(self) -> bool:
        return (self.root / "BOOTSTRAP.md").exists()


workspace = Workspace()
