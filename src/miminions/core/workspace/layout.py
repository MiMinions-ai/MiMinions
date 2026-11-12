from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Final, List


BOOTSTRAP_PROMPT_FILES: Final[List[str]] = [
    "AGENTS.md",
    "USER.md",
    "TOOLS.md",
    "IDENTITY.md",
]


@dataclass(frozen=True)
class WorkspaceLayout:
    """
    Standard on-disk layout for a MiMinions workspace.

    root/
      prompt/
      memory/
      skills/
      sessions/
      data/
    """
    root: Path

    @staticmethod
    def from_root(root_path: str | Path) -> "WorkspaceLayout":
        return WorkspaceLayout(Path(root_path).expanduser().resolve())

    @property
    def prompt_dir(self) -> Path:
        return self.root / "prompt"

    @property
    def memory_dir(self) -> Path:
        return self.root / "memory"

    @property
    def skills_dir(self) -> Path:
        return self.root / "skills"

    @property
    def sessions_dir(self) -> Path:
        return self.root / "sessions"

    @property
    def data_dir(self) -> Path:
        return self.root / "data"

    def prompt_file_path(self, filename: str) -> Path:
        return self.prompt_dir / filename

    def memory_file_path(self, filename: str) -> Path:
        return self.memory_dir / filename