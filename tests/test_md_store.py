from pathlib import Path

from miminions.memory.md_store import (
    append_history,
    read_memory,
    upsert_memory_section,
    write_memory,
)
from miminions.workspace_fs.bootstrap import init_workspace


def test_read_memory_returns_existing_or_bootstrapped_content(tmp_path: Path):
    init_workspace(tmp_path)

    content = read_memory(tmp_path)

    assert isinstance(content, str)
    assert len(content) > 0
    assert (tmp_path / "memory" / "MEMORY.md").exists()
    assert (tmp_path / "memory" / "HISTORY.md").exists()


def test_write_memory_replaces_memory_content(tmp_path: Path):
    init_workspace(tmp_path)

    write_memory(tmp_path, "# Memory\n\nThis is replaced content.\n")
    content = read_memory(tmp_path)

    assert content == "# Memory\n\nThis is replaced content.\n"


def test_append_history_appends_bullet_line(tmp_path: Path):
    init_workspace(tmp_path)

    history_path = append_history(tmp_path, "Completed first test task.")
    text = history_path.read_text(encoding="utf-8")

    assert history_path == (tmp_path / "memory" / "HISTORY.md")
    assert "- Completed first test task.\n" in text


def test_upsert_memory_section_adds_new_section(tmp_path: Path):
    init_workspace(tmp_path)

    upsert_memory_section(
        tmp_path,
        "User Preferences",
        ["Prefers concise output", "Uses repo-local workspaces"],
    )

    text = read_memory(tmp_path)

    assert "## User Preferences" in text
    assert "- Prefers concise output" in text
    assert "- Uses repo-local workspaces" in text


def test_upsert_memory_section_replaces_existing_section(tmp_path: Path):
    init_workspace(tmp_path)

    write_memory(
        tmp_path,
        "# Memory\n\n## User Preferences\n- old item\n\n## Other Section\n- keep me\n",
    )

    upsert_memory_section(
        tmp_path,
        "User Preferences",
        ["new item 1", "new item 2"],
    )

    text = read_memory(tmp_path)

    assert "## User Preferences" in text
    assert "- new item 1" in text
    assert "- new item 2" in text
    assert "- old item" not in text
    assert "## Other Section" in text
    assert "- keep me" in text