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

    content_is_string = isinstance(content, str)
    content_type = type(content)
    assert content_is_string, f"expect read_memory returns string content as True, got {content_type}"
    content_length = len(content)
    assert content_length > 0, f"expect len(content) > 0, got {content_length}"
    memory_file_exists = (tmp_path / "memory" / "MEMORY.md").exists()
    assert memory_file_exists, f"expect read_memory bootstrap creates memory/MEMORY.md as True, got {memory_file_exists}"
    history_file_exists = (tmp_path / "memory" / "HISTORY.md").exists()
    assert history_file_exists, f"expect read_memory bootstrap creates memory/HISTORY.md as True, got {history_file_exists}"


def test_write_memory_replaces_memory_content(tmp_path: Path):
    init_workspace(tmp_path)

    write_memory(tmp_path, "# Memory\n\nThis is replaced content.\n")
    content = read_memory(tmp_path)

    assert content == "# Memory\n\nThis is replaced content.\n", f"expect write_memory fully replaces memory file content as '# Memory\\n\\nThis is replaced content.\\n', got {content}"


def test_append_history_appends_bullet_line(tmp_path: Path):
    init_workspace(tmp_path)

    history_path = append_history(tmp_path, "Completed first test task.")
    text = history_path.read_text(encoding="utf-8")

    assert history_path == (tmp_path / "memory" / "HISTORY.md"), f"expect tmp_path / 'memory' / 'HISTORY.md', got {history_path}"
    assert "- Completed first test task.\n" in text, f"expect contains '- Completed first test task.\\n', got {text}"


def test_upsert_memory_section_adds_new_section(tmp_path: Path):
    init_workspace(tmp_path)

    upsert_memory_section(
        tmp_path,
        "User Preferences",
        ["Prefers concise output", "Uses repo-local workspaces"],
    )

    text = read_memory(tmp_path)

    assert "## User Preferences" in text, f"expect contains '## User Preferences', got {text}"
    assert "- Prefers concise output" in text, f"expect contains '- Prefers concise output', got {text}"
    assert "- Uses repo-local workspaces" in text, f"expect contains '- Uses repo-local workspaces', got {text}"


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

    assert "## User Preferences" in text, f"expect contains '## User Preferences', got {text}"
    assert "- new item 1" in text, f"expect contains '- new item 1', got {text}"
    assert "- new item 2" in text, f"expect contains '- new item 2', got {text}"
    assert "- old item" not in text, f"expect not contains '- old item', got {text}"
    assert "## Other Section" in text, f"expect contains '## Other Section', got {text}"
    assert "- keep me" in text, f"expect contains '- keep me', got {text}"
