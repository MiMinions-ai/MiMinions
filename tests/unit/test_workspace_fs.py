from pathlib import Path

import pytest

from miminions.workspace_fs import (
    BOOTSTRAP_PROMPT_FILES,
    WorkspaceLayout,
    init_workspace,
    list_skills,
    read_memory_md,
    read_prompt_files,
    read_skill,
)


def test_workspace_layout_resolves_standard_paths(tmp_path):
    layout = WorkspaceLayout.from_root(tmp_path / "ws")

    assert layout.root == (tmp_path / "ws").resolve()
    assert layout.prompt_dir == layout.root / "prompt"
    assert layout.memory_dir == layout.root / "memory"
    assert layout.skills_dir == layout.root / "skills"
    assert layout.sessions_dir == layout.root / "sessions"
    assert layout.data_dir == layout.root / "data"
    assert layout.prompt_file_path("USER.md") == layout.root / "prompt" / "USER.md"
    assert layout.memory_file_path("MEMORY.md") == layout.root / "memory" / "MEMORY.md"


def test_init_workspace_creates_templates_and_skips_existing_files(tmp_path):
    first = init_workspace(tmp_path)

    assert first["root"] == str(tmp_path.resolve())
    assert len(first["created"]) >= 7
    assert first["skipped"] == []
    for filename in BOOTSTRAP_PROMPT_FILES:
        assert (tmp_path / "prompt" / filename).exists()
    assert (tmp_path / "memory" / "MEMORY.md").exists()
    assert (tmp_path / "skills" / "core" / "SKILL.md").exists()

    user_file = tmp_path / "prompt" / "USER.md"
    user_file.write_text("custom", encoding="utf-8")
    second = init_workspace(tmp_path)

    assert second["created"] == []
    assert str(user_file) in second["skipped"]
    assert user_file.read_text(encoding="utf-8") == "custom"


def test_init_workspace_overwrite_replaces_existing_templates(tmp_path):
    init_workspace(tmp_path)
    user_file = tmp_path / "prompt" / "USER.md"
    user_file.write_text("custom", encoding="utf-8")

    result = init_workspace(tmp_path, overwrite=True)

    assert str(user_file) in result["created"]
    assert user_file.read_text(encoding="utf-8").startswith("# USER")


def test_readers_return_prompt_memory_and_sorted_skills(tmp_path):
    init_workspace(tmp_path)
    (tmp_path / "prompt" / "AGENTS.md").write_text("agents", encoding="utf-8")
    (tmp_path / "memory" / "MEMORY.md").write_text("remember", encoding="utf-8")
    (tmp_path / "skills" / "zeta").mkdir()
    (tmp_path / "skills" / "zeta" / "SKILL.md").write_text("z", encoding="utf-8")
    (tmp_path / "skills" / "alpha").mkdir()
    (tmp_path / "skills" / "alpha" / "SKILL.md").write_text("a", encoding="utf-8")
    (tmp_path / "skills" / "ignored.txt").write_text("nope", encoding="utf-8")

    prompts = read_prompt_files(tmp_path)
    skills = list_skills(tmp_path)

    assert prompts["AGENTS.md"] == "agents"
    assert read_memory_md(tmp_path) == "remember"
    assert [skill["name"] for skill in skills] == ["alpha", "core", "zeta"]
    assert read_skill(skills[0]["path"]) == "a"


def test_readers_handle_missing_files(tmp_path):
    assert read_prompt_files(tmp_path) == {}
    assert read_memory_md(tmp_path) == ""
    assert list_skills(tmp_path) == []

    with pytest.raises(FileNotFoundError, match="Skill file not found"):
        read_skill(tmp_path / "missing" / "SKILL.md")
