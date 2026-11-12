from __future__ import annotations

from pathlib import Path
from typing import Dict, List

from .layout import WorkspaceLayout, BOOTSTRAP_PROMPT_FILES


def read_prompt_files(root_path: str | Path) -> Dict[str, str]:
    """
    Read bootstrap prompt files from root/prompt/*.md.
    Returns a dict like {"AGENTS.md": "...", ...}.
    Missing files are simply omitted.
    """
    layout = WorkspaceLayout.from_root(root_path)
    out: Dict[str, str] = {}

    for fname in BOOTSTRAP_PROMPT_FILES:
        p = layout.prompt_file_path(fname)
        if p.exists() and p.is_file():
            out[fname] = p.read_text(encoding="utf-8")

    return out


def read_memory_md(root_path: str | Path) -> str:
    """
    Read root/memory/MEMORY.md. Returns "" if missing.
    """
    layout = WorkspaceLayout.from_root(root_path)
    p = layout.memory_file_path("MEMORY.md")
    if not p.exists() or not p.is_file():
        return ""
    return p.read_text(encoding="utf-8")


def list_skills(root_path: str | Path) -> List[dict]:
    """
    Discover skills in root/skills/<skill>/SKILL.md.
    Returns list of {"name": str, "path": str}.
    """
    layout = WorkspaceLayout.from_root(root_path)
    skills: List[dict] = []

    if not layout.skills_dir.exists():
        return skills

    for skill_dir in layout.skills_dir.iterdir():
        if not skill_dir.is_dir():
            continue
        skill_file = skill_dir / "SKILL.md"
        if skill_file.exists() and skill_file.is_file():
            skills.append({"name": skill_dir.name, "path": str(skill_file)})

    # stable ordering
    skills.sort(key=lambda x: x["name"])
    return skills


def read_skill(skill_path: str | Path) -> str:
    """
    Read a specific SKILL.md file.
    """
    p = Path(skill_path).expanduser().resolve()
    if not p.exists() or not p.is_file():
        raise FileNotFoundError(f"Skill file not found: {p}")
    return p.read_text(encoding="utf-8")