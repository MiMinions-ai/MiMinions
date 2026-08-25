import json

from miminions.cli.knowledge import knowledge_cli, load_knowledge, save_knowledge


def _entry(content="First"):
    return {
        "title": "Guide",
        "content": content,
        "category": "docs",
        "tags": ["cli"],
        "version": "1.0",
        "status": "active",
        "created_at": "created",
        "updated_at": None,
        "versions": [{"version": "1.0", "content": content, "timestamp": "created"}],
    }


def test_knowledge_storage_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.knowledge.get_config_dir", lambda: tmp_path)

    loaded_knowledge = load_knowledge()
    assert loaded_knowledge == {}, f"expect load_knowledge returns empty mapping when knowledge store is absent as {{}}, got {loaded_knowledge}"
    save_knowledge({"k1": _entry()})

    loaded_knowledge = load_knowledge()
    title = loaded_knowledge["k1"]["title"]
    assert title == "Guide", f"expect save_knowledge persists entry title and load_knowledge restores it as 'Guide', got {title}"


def test_knowledge_add_list_show_update_and_versions(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.knowledge.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("miminions.cli.knowledge.uuid.uuid4", lambda: "abcd1234-ffff")

    added = isolated_cli_runner.invoke(
        knowledge_cli,
        [
            "add",
            "--title",
            "Guide",
            "--content",
            "First",
            "--category",
            "docs",
            "--tags",
            "cli, tests",
        ],
    )
    assert added.exit_code == 0, f"expect cli exit code 0, got {added.exit_code} with output: {added.output}"
    assert "Knowledge entry 'Guide' added successfully with ID: abcd1234" in added.output, f"expect knowledge add command reports created entry id for the new entry as {"Knowledge entry 'Guide' added successfully with ID: abcd1234"}, got {added.output}"

    listed = isolated_cli_runner.invoke(knowledge_cli, ["list"])
    assert "abcd1234: Guide (v1.0, docs, active)" in listed.output, f"expect knowledge list output includes created entry id, title, version, category, and status as 'abcd1234: Guide (v1.0, docs, active)', got {listed.output}"

    shown = isolated_cli_runner.invoke(knowledge_cli, ["show", "abcd1234"])
    assert "Tags: cli, tests" in shown.output, f"expect knowledge show output lists configured tags for selected entry as 'Tags: cli, tests', got {shown.output}"
    assert "Content:\nFirst" in shown.output, f"expect knowledge show output includes entry content body for selected entry as 'Content:\nFirst', got {shown.output}"

    updated = isolated_cli_runner.invoke(
        knowledge_cli,
        [
            "update",
            "abcd1234",
            "--title",
            "Guide v2",
            "--content",
            "Second",
            "--tags",
            "updated",
        ],
    )
    assert updated.exit_code == 0, f"expect cli exit code 0, got {updated.exit_code} with output: {updated.output}"
    assert "updated successfully" in updated.output, f"expect knowledge update command confirms successful entry update as 'updated successfully', got {updated.output}"

    data = json.loads((tmp_path / "knowledge.json").read_text(encoding="utf-8"))
    assert data["abcd1234"]["title"] == "Guide v2", f"expect updated knowledge title is persisted to storage after knowledge update command as 'Guide v2', got {data['abcd1234']['title']}"
    assert data["abcd1234"]["version"] == "1.1", f"expect knowledge entry semantic version increments after content update as '1.1', got {data['abcd1234']['version']}"
    assert data["abcd1234"]["versions"][-1]["content"] == "Second", f"expect latest version history record stores updated content text as 'Second', got {data['abcd1234']['versions'][-1]['content']}"

    versions = isolated_cli_runner.invoke(knowledge_cli, ["version", "abcd1234"])
    assert "v1.0" in versions.output, f"expect version command output includes original version history entry as 'v1.0', got {versions.output}"
    assert "v1.1 (current)" in versions.output, f"expect version command output marks latest version as current as 'v1.1 (current)', got {versions.output}"


def test_knowledge_revert_customize_remove_and_missing_paths(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.knowledge.get_config_dir", lambda: tmp_path)
    save_knowledge(
        {
            "k1": {
                **_entry("Second"),
                "version": "1.1",
                "versions": [
                    {"version": "1.0", "content": "First", "timestamp": "t1"},
                    {"version": "1.1", "content": "Second", "timestamp": "t2"},
                ],
            }
        }
    )

    missing_version = isolated_cli_runner.invoke(
        knowledge_cli, ["revert", "k1", "--version", "2.0"]
    )
    assert missing_version.exit_code == 0, f"expect cli exit code 0, got {missing_version.exit_code} with output: {missing_version.output}"
    assert "Version '2.0' not found" in missing_version.output, f"expect revert command reports missing target version when requested version does not exist as {"Version '2.0' not found"}, got {missing_version.output}"

    reverted = isolated_cli_runner.invoke(
        knowledge_cli, ["revert", "k1", "--version", "1.0"]
    )
    assert reverted.exit_code == 0, f"expect cli exit code 0, got {reverted.exit_code} with output: {reverted.output}"
    assert "reverted to version 1.0" in reverted.output, f"expect revert command confirms selected target version restoration as 'reverted to version 1.0', got {reverted.output}"
    loaded_knowledge = load_knowledge()
    content = loaded_knowledge["k1"]["content"]
    assert content == "First", f"expect reverted knowledge entry content matches selected historical version content as 'First', got {content}"

    customized = isolated_cli_runner.invoke(
        knowledge_cli,
        ["customize", "k1", "--template", "short", "--format", "markdown"],
    )
    assert customized.exit_code == 0, f"expect cli exit code 0, got {customized.exit_code} with output: {customized.output}"
    assert "Template 'short' applied" in customized.output, f"expect customize command reports selected template application as {"Template 'short' applied"}, got {customized.output}"
    assert "# Guide" in customized.output, f"expect customize command renders markdown heading for knowledge entry title as '# Guide', got {customized.output}"

    as_json = isolated_cli_runner.invoke(knowledge_cli, ["customize", "k1", "--format", "json"])
    assert '"template": "short"' in as_json.output, f"expect customize command json output reports selected template metadata as {'"template": "short"'}, got {as_json.output}"

    removed = isolated_cli_runner.invoke(knowledge_cli, ["remove", "k1", "--yes"])
    assert removed.exit_code == 0, f"expect cli exit code 0, got {removed.exit_code} with output: {removed.output}"
    assert "removed successfully" in removed.output, f"expect remove command confirms knowledge entry deletion as 'removed successfully', got {removed.output}"

    for command in (
        ["show", "missing"],
        ["version", "missing"],
        ["update", "missing", "--title", "x"],
        ["customize", "missing"],
        ["remove", "missing", "--yes"],
        ["revert", "missing", "--version", "1.0"],
    ):
        result = isolated_cli_runner.invoke(knowledge_cli, command)
        assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
        assert "not found" in result.output, f"expect knowledge command reports missing-entry path for unknown id as 'not found', got {result.output}"
