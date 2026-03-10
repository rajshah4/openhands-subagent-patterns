from __future__ import annotations

from pathlib import Path

from openhands.sdk.context import Skill


ROOT = Path(__file__).resolve().parents[2]
SKILLS_DIR = ROOT / "skills"


def load_skill(skill_name: str) -> Skill:
    skill_path = SKILLS_DIR / skill_name / "SKILL.md"
    return Skill(
        name=skill_name,
        content=skill_path.read_text(encoding="utf-8"),
        source=str(skill_path),
        trigger=None,
    )
