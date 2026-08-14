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

    assert load_knowledge() == {}
    save_knowledge({"k1": _entry()})

    assert load_knowledge()["k1"]["title"] == "Guide"


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
    assert added.exit_code == 0
    assert "Knowledge entry 'Guide' added successfully with ID: abcd1234" in added.output

    listed = isolated_cli_runner.invoke(knowledge_cli, ["list"])
    assert "abcd1234: Guide (v1.0, docs, active)" in listed.output

    shown = isolated_cli_runner.invoke(knowledge_cli, ["show", "abcd1234"])
    assert "Tags: cli, tests" in shown.output
    assert "Content:\nFirst" in shown.output

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
    assert updated.exit_code == 0
    assert "updated successfully" in updated.output

    data = json.loads((tmp_path / "knowledge.json").read_text(encoding="utf-8"))
    assert data["abcd1234"]["title"] == "Guide v2"
    assert data["abcd1234"]["version"] == "1.1"
    assert data["abcd1234"]["versions"][-1]["content"] == "Second"

    versions = isolated_cli_runner.invoke(knowledge_cli, ["version", "abcd1234"])
    assert "v1.0" in versions.output
    assert "v1.1 (current)" in versions.output


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
    assert missing_version.exit_code == 0
    assert "Version '2.0' not found" in missing_version.output

    reverted = isolated_cli_runner.invoke(
        knowledge_cli, ["revert", "k1", "--version", "1.0"]
    )
    assert reverted.exit_code == 0
    assert "reverted to version 1.0" in reverted.output
    assert load_knowledge()["k1"]["content"] == "First"

    customized = isolated_cli_runner.invoke(
        knowledge_cli,
        ["customize", "k1", "--template", "short", "--format", "markdown"],
    )
    assert customized.exit_code == 0
    assert "Template 'short' applied" in customized.output
    assert "# Guide" in customized.output

    as_json = isolated_cli_runner.invoke(knowledge_cli, ["customize", "k1", "--format", "json"])
    assert '"template": "short"' in as_json.output

    removed = isolated_cli_runner.invoke(knowledge_cli, ["remove", "k1", "--yes"])
    assert removed.exit_code == 0
    assert "removed successfully" in removed.output

    for command in (
        ["show", "missing"],
        ["version", "missing"],
        ["update", "missing", "--title", "x"],
        ["customize", "missing"],
        ["remove", "missing", "--yes"],
        ["revert", "missing", "--version", "1.0"],
    ):
        result = isolated_cli_runner.invoke(knowledge_cli, command)
        assert result.exit_code == 0
        assert "not found" in result.output
