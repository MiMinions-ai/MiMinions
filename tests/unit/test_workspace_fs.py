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

    assert layout.root == (tmp_path / "ws").resolve(), f"expect {(tmp_path / 'ws').resolve()}, got {layout.root}"
    assert layout.prompt_dir == layout.root / "prompt", f"expect {layout.root} / 'prompt', got {layout.prompt_dir}"
    assert layout.memory_dir == layout.root / "memory", f"expect {layout.root} / 'memory', got {layout.memory_dir}"
    assert layout.skills_dir == layout.root / "skills", f"expect {layout.root} / 'skills', got {layout.skills_dir}"
    assert layout.sessions_dir == layout.root / "sessions", f"expect {layout.root} / 'sessions', got {layout.sessions_dir}"
    assert layout.data_dir == layout.root / "data", f"expect {layout.root} / 'data', got {layout.data_dir}"
    assert layout.prompt_file_path("USER.md") == layout.root / "prompt" / "USER.md", f"expect {layout.root} / 'prompt' / 'USER.md', got {layout.prompt_file_path('USER.md')}"
    assert layout.memory_file_path("MEMORY.md") == layout.root / "memory" / "MEMORY.md", f"expect {layout.root} / 'memory' / 'MEMORY.md', got {layout.memory_file_path('MEMORY.md')}"


def test_init_workspace_creates_templates_and_skips_existing_files(tmp_path):
    first = init_workspace(tmp_path)

    assert first["root"] == str(tmp_path.resolve()), f"expect {tmp_path.resolve()!s}, got {first['root']}"
    assert len(first["created"]) >= 7, f"expect the number of created files to be at least 7, got {len(first['created'])}"
    assert first["skipped"] == [], f"expect no skipped files, got {first['skipped']}"
    for filename in BOOTSTRAP_PROMPT_FILES:
        prompt_file_exists = (tmp_path / "prompt" / filename).exists()
        assert prompt_file_exists, f"expect init_workspace creates prompt file {filename}, got {prompt_file_exists}"
    memory_file_exists = (tmp_path / "memory" / "MEMORY.md").exists()
    assert memory_file_exists, f"expect init_workspace creates memory/MEMORY.md, got {memory_file_exists}"
    skill_file_exists = (tmp_path / "skills" / "core" / "SKILL.md").exists()
    assert skill_file_exists, f"expect init_workspace creates skills/core/SKILL.md, got {skill_file_exists}"

    user_file = tmp_path / "prompt" / "USER.md"
    user_file.write_text("custom", encoding="utf-8")
    second = init_workspace(tmp_path)

    assert second["created"] == [], f"expect no created files, got {second['created']}"
    assert str(user_file) in second["skipped"], f"expect {user_file!s} exists in skipped files, got {second['skipped']}"
    assert user_file.read_text(encoding="utf-8") == "custom", f"expect 'custom' in the user_file, got {user_file.read_text(encoding='utf-8')}"


def test_init_workspace_overwrite_replaces_existing_templates(tmp_path):
    init_workspace(tmp_path)
    user_file = tmp_path / "prompt" / "USER.md"
    user_file.write_text("custom", encoding="utf-8")

    result = init_workspace(tmp_path, overwrite=True)

    assert str(user_file) in result["created"], f"expect {user_file!s} exists in created files, got {result['created']}"
    assert user_file.read_text(encoding="utf-8").startswith("# USER"), f"expect '# USER' at the start of the user_file, got {user_file.read_text(encoding='utf-8').startswith('# USER')}"


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

    assert prompts["AGENTS.md"] == "agents", f"expect prompts['AGENTS.md'] == 'agents', got {prompts['AGENTS.md']}"
    assert read_memory_md(tmp_path) == "remember", f"expect 'remember' from memory file, got {read_memory_md(tmp_path)}"
    assert [skill["name"] for skill in skills] == ["alpha", "core", "zeta"], f"expect ['alpha', 'core', 'zeta'] as the skills name order, got {[skill['name'] for skill in skills]}"
    assert read_skill(skills[0]["path"]) == "a", f"expect 'a' from skill file, got {read_skill(skills[0]['path'])}"


def test_readers_handle_missing_files(tmp_path):
    assert read_prompt_files(tmp_path) == {}, f"expect {{}} as the result for missing prompt files, got {read_prompt_files(tmp_path)}"
    assert read_memory_md(tmp_path) == "", f"expect '' from reading memory file of empty path, got {read_memory_md(tmp_path)}"
    assert list_skills(tmp_path) == [], f"expect [] from listing skills of empty path, got {list_skills(tmp_path)}"

    with pytest.raises(FileNotFoundError, match="Skill file not found"):
        read_skill(tmp_path / "missing" / "SKILL.md")
