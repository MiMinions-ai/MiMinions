from __future__ import annotations

from pathlib import Path
from typing import Iterable

from miminions.workspace_fs.layout import WorkspaceLayout


DEFAULT_MEMORY_TEMPLATE = """# Memory

Stable facts, preferences, and durable workspace knowledge go here.
"""

DEFAULT_HISTORY_TEMPLATE = """# History

Session summaries and notable completed tasks go here.
"""


def _ensure_memory_files(root_path: str | Path) -> WorkspaceLayout:
    """Ensure memory directory and core markdown files exist."""
    layout = WorkspaceLayout.from_root(root_path)
    layout.memory_dir.mkdir(parents=True, exist_ok=True)

    memory_file = layout.memory_dir / "MEMORY.md"
    history_file = layout.memory_dir / "HISTORY.md"

    if not memory_file.exists():
        memory_file.write_text(DEFAULT_MEMORY_TEMPLATE, encoding="utf-8")

    if not history_file.exists():
        history_file.write_text(DEFAULT_HISTORY_TEMPLATE, encoding="utf-8")

    return layout


def read_memory(root_path: str | Path) -> str:
    """Read MEMORY.md content, creating the file if needed."""
    layout = _ensure_memory_files(root_path)
    memory_file = layout.memory_dir / "MEMORY.md"
    return memory_file.read_text(encoding="utf-8")


def write_memory(root_path: str | Path, content: str) -> Path:
    """Replace MEMORY.md with the provided content."""
    if content is None:
        raise ValueError("content cannot be None")

    layout = _ensure_memory_files(root_path)
    memory_file = layout.memory_dir / "MEMORY.md"
    memory_file.write_text(content, encoding="utf-8")
    return memory_file


def append_history(root_path: str | Path, line: str) -> Path:
    """Append a single history entry to HISTORY.md."""
    if line is None:
        raise ValueError("line cannot be None")

    text = line.strip()
    if not text:
        raise ValueError("line cannot be empty")

    layout = _ensure_memory_files(root_path)
    history_file = layout.memory_dir / "HISTORY.md"

    existing = history_file.read_text(encoding="utf-8")
    needs_newline = bool(existing) and not existing.endswith("\n")

    with history_file.open("a", encoding="utf-8") as f:
        if needs_newline:
            f.write("\n")
        f.write(f"- {text}\n")

    return history_file


def upsert_memory_section(
    root_path: str | Path,
    heading: str,
    bullets: Iterable[str],
) -> Path:
    """Insert or replace a markdown section in MEMORY.md.

    Example heading:
        "User Preferences"

    Resulting section:
        ## User Preferences
        - item 1
        - item 2
    """
    if heading is None:
        raise ValueError("heading cannot be None")

    clean_heading = heading.strip()
    if not clean_heading:
        raise ValueError("heading cannot be empty")

    bullet_lines = [str(item).strip() for item in bullets if str(item).strip()]
    section_lines = [f"## {clean_heading}"]
    section_lines.extend(f"- {item}" for item in bullet_lines)
    new_section = "\n".join(section_lines).rstrip() + "\n"

    current = read_memory(root_path)
    lines = current.splitlines()

    target_heading = f"## {clean_heading}"
    start_idx = None
    end_idx = None

    for i, line in enumerate(lines):
        if line.strip() == target_heading:
            start_idx = i
            break

    if start_idx is None:
        updated = current.rstrip()
        if updated:
            updated += "\n\n"
        updated += new_section
        write_memory(root_path, updated)
        layout = WorkspaceLayout.from_root(root_path)
        return layout.memory_dir / "MEMORY.md"

    end_idx = len(lines)
    for i in range(start_idx + 1, len(lines)):
        if lines[i].startswith("## "):
            end_idx = i
            break

    before = "\n".join(lines[:start_idx]).rstrip()
    after = "\n".join(lines[end_idx:]).lstrip()

    parts = []
    if before:
        parts.append(before)
    parts.append(new_section.rstrip())
    if after:
        parts.append(after)

    updated = "\n\n".join(parts).rstrip() + "\n"
    write_memory(root_path, updated)

    layout = WorkspaceLayout.from_root(root_path)
    return layout.memory_dir / "MEMORY.md"