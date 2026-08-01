"""Skill Manager — Hermes-style learning loop: observe → distill → reuse → refine."""

from __future__ import annotations

import json
import re
import time
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "skills"


class SkillManager:
    def __init__(self, root: Optional[Path] = None):
        self.root = root or DATA_DIR
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError:
            self.root = Path("/tmp/vrav_skills")
            self.root.mkdir(parents=True, exist_ok=True)
        self.index_path = self.root / "index.json"
        if not self.index_path.exists():
            self._write_index({})

    def _load_index(self) -> Dict[str, Any]:
        try:
            return json.loads(self.index_path.read_text(encoding="utf-8") or "{}")
        except OSError:
            return {}

    def _write_index(self, idx: Dict[str, Any]) -> None:
        try:
            self.index_path.write_text(json.dumps(idx, ensure_ascii=False, indent=2), encoding="utf-8")
        except OSError:
            pass

    def list_skills(self) -> List[Dict[str, Any]]:
        return list(self._load_index().values())

    def get_skill(self, name: str) -> Optional[str]:
        path = self.root / f"{name}.md"
        if path.exists():
            try:
                return path.read_text(encoding="utf-8")
            except OSError:
                return None
        return None

    def skill_summaries_for_prompt(self, limit: int = 15) -> str:
        skills = self.list_skills()[:limit]
        if not skills:
            return ""
        lines = ["## Available skills (use when relevant)"]
        for s in skills:
            lines.append(f"- **{s['name']}**: {s.get('description', '')[:120]}")
        return "\n".join(lines)

    def record_success(
        self, task_pattern: str, steps: List[str], outcome: str, tags: Optional[List[str]] = None,
    ) -> Optional[str]:
        idx = self._load_index()
        key = self._normalize_pattern(task_pattern)
        entry = idx.get(key) or {
            "name": key, "description": task_pattern[:200], "count": 0,
            "steps_examples": [], "outcomes": [], "tags": tags or [],
            "skill_created": False, "updated_at": time.time(),
        }
        entry["count"] = int(entry.get("count", 0)) + 1
        entry["steps_examples"].append(steps[:12])
        entry["outcomes"].append(outcome[:300])
        entry["updated_at"] = time.time()
        entry["steps_examples"] = entry["steps_examples"][-5:]
        entry["outcomes"] = entry["outcomes"][-5:]
        created_name = None
        if entry["count"] >= 3 and not entry.get("skill_created"):
            created_name = self._distill_skill(entry)
            entry["skill_created"] = True
            entry["skill_file"] = created_name
        idx[key] = entry
        self._write_index(idx)
        return created_name

    def refine_skill(self, name: str, note: str) -> bool:
        path = self.root / f"{name}.md"
        if not path.exists():
            return False
        try:
            content = path.read_text(encoding="utf-8")
            content += f"\n\n## Refinement ({time.strftime('%Y-%m-%d')})\n{note}\n"
            path.write_text(content, encoding="utf-8")
            return True
        except OSError:
            return False

    def _normalize_pattern(self, text: str) -> str:
        t = text.lower().strip()
        t = re.sub(r"[^a-zа-я0-9\s]", "", t)
        t = re.sub(r"\s+", "_", t)[:48]
        return t or f"skill_{uuid.uuid4().hex[:8]}"

    def _distill_skill(self, entry: Dict[str, Any]) -> str:
        name = entry["name"]
        steps = entry.get("steps_examples", [[]])[-1]
        steps_md = "\n".join(f"{i+1}. {s}" for i, s in enumerate(steps)) or "1. Analyze\n2. Act\n3. Verify"
        body = f"""# Skill: {name}

## Description
{entry.get('description', name)}

## When to use
When the user asks something similar to: "{entry.get('description', '')[:150]}"

## Procedure
{steps_md}

## Verification
- Confirm facts with tools when legal or numerical claims appear
- State confidence level

## Tags
{', '.join(entry.get('tags') or [])}

## Stats
Successful runs before distillation: {entry.get('count', 0)}
"""
        path = self.root / f"{name}.md"
        try:
            path.write_text(body, encoding="utf-8")
        except OSError:
            pass
        return name


skill_manager = SkillManager()
