from __future__ import annotations

from pathlib import Path
from typing import Dict, Any

from .layout import WorkspaceLayout, BOOTSTRAP_PROMPT_FILES


_DEFAULT_TEMPLATES: Dict[str, str] = {
    "prompt/AGENTS.md": """# AGENTS
- what this agent is for
- style rules
- task completion rules
""",
    "prompt/USER.md": """# USER
- user preferences
- output format preferences
""",
    "prompt/TOOLS.md": """# TOOLS
- tool safety rules
- allowed actions
- file boundaries: write under data/
""",
    "prompt/IDENTITY.md": """# IDENTITY
- workspace identity and goals
- constraints
""",
    "memory/MEMORY.md": """# Long-term Memory
## Facts
## Decisions
## Preferences
""",
    "memory/HISTORY.md": """# History (append-only)
""",
    "skills/core/SKILL.md": """# core
Use this as the default skill guidance.

## rules
- keep responses short
- ask for missing info only when needed
""",
}


def init_workspace(root_path: str | Path, overwrite: bool = False) -> Dict[str, Any]:
    """
    Create the workspace folder structure + default template files.

    - Does NOT overwrite existing files unless overwrite=True.
    - Returns a summary dict: created/skipped + resolved root path.
    """
    layout = WorkspaceLayout.from_root(root_path)

    # Directories
    dirs = [
        layout.root,
        layout.prompt_dir,
        layout.memory_dir,
        layout.skills_dir,
        layout.sessions_dir,
        layout.data_dir,
    ]
    for d in dirs:
        d.mkdir(parents=True, exist_ok=True)

    created = []
    skipped = []

    for rel_path, content in _DEFAULT_TEMPLATES.items():
        p = layout.root / rel_path
        p.parent.mkdir(parents=True, exist_ok=True)

        if p.exists() and not overwrite:
            skipped.append(str(p))
            continue

        p.write_text(content, encoding="utf-8")
        created.append(str(p))

    # sanity: ensure bootstrap prompt files exist (even if templates changed)
    for fname in BOOTSTRAP_PROMPT_FILES:
        p = layout.prompt_file_path(fname)
        if not p.exists():
            p.write_text(f"# {fname.removesuffix('.md')}\n", encoding="utf-8")
            created.append(str(p))

    return {
        "root": str(layout.root),
        "created": created,
        "skipped": skipped,
    }