import json

import pytest

from miminions.cli.workspace import _parse_json_or_shorthand, workspace_cli
from miminions.core.workspace import Rule, RulePriority, Workspace, WorkspaceManager


def _save_workspace(config_dir, workspace):
    manager = WorkspaceManager(config_dir)
    manager.save_workspaces({workspace.id: workspace})
    return manager


def test_parse_json_or_shorthand():
    assert _parse_json_or_shorthand(None, "condition") == {}
    assert _parse_json_or_shorthand("state_equals", "condition") == {
        "type": "state_equals"
    }
    assert _parse_json_or_shorthand('{"type": "always"}', "condition") == {
        "type": "always"
    }

    with pytest.raises(Exception, match="Invalid JSON"):
        _parse_json_or_shorthand("{bad", "condition")


def test_workspace_add_list_show_and_duplicate_name(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.workspace.get_config_dir", lambda: tmp_path)

    added = isolated_cli_runner.invoke(
        workspace_cli, ["add", "--name", "Main", "--description", "Primary"]
    )
    assert added.exit_code == 0
    assert "Workspace 'Main' created successfully" in added.output

    duplicate = isolated_cli_runner.invoke(workspace_cli, ["add", "--name", "Main"])
    assert duplicate.exit_code == 0
    assert "already exists" in duplicate.output

    listed = isolated_cli_runner.invoke(workspace_cli, ["list"])
    assert listed.exit_code == 0
    assert "Main" in listed.output
    assert "Description: Primary" in listed.output

    shown = isolated_cli_runner.invoke(workspace_cli, ["show", "Main"])
    assert shown.exit_code == 0
    assert "Workspace: Main" in shown.output
    assert "Network Summary:" in shown.output


def test_workspace_add_sample_and_init_files_with_custom_root(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.workspace.get_config_dir", lambda: tmp_path)
    root = tmp_path / "workspace-root"

    result = isolated_cli_runner.invoke(
        workspace_cli,
        [
            "add",
            "--name",
            "Sample",
            "--description",
            "Demo",
            "--sample",
            "--init-files",
            "--root-path",
            str(root),
        ],
    )

    assert result.exit_code == 0
    assert "Sample workspace 'Sample' created successfully" in result.output
    assert "Initialized workspace files at:" in result.output
    assert (root / "prompt" / "AGENTS.md").exists()
    data = json.loads((tmp_path / "workspaces.json").read_text(encoding="utf-8"))
    workspace_data = next(iter(data.values()))
    assert workspace_data["root_path"] == str(root.resolve())
    assert len(workspace_data["nodes"]) == 3
    assert len(workspace_data["rules"]) == 2


def test_workspace_update_set_state_remove_and_missing_paths(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.workspace.get_config_dir", lambda: tmp_path)
    first = Workspace(id="ws1", name="One")
    second = Workspace(id="ws2", name="Two")
    WorkspaceManager(tmp_path).save_workspaces({first.id: first, second.id: second})

    duplicate = isolated_cli_runner.invoke(
        workspace_cli, ["update", "One", "--name", "Two"]
    )
    assert duplicate.exit_code == 0
    assert "already exists" in duplicate.output

    updated = isolated_cli_runner.invoke(
        workspace_cli, ["update", "One", "--name", "Renamed", "--description", "New"]
    )
    assert updated.exit_code == 0
    assert "Workspace updated successfully" in updated.output

    set_json = isolated_cli_runner.invoke(
        workspace_cli, ["set-state", "Renamed", "--key", "count", "--value", "3"]
    )
    assert set_json.exit_code == 0
    assert "Set state 'count' = '3'" in set_json.output

    set_string = isolated_cli_runner.invoke(
        workspace_cli, ["set-state", "Renamed", "--key", "mode", "--value", "ready"]
    )
    assert set_string.exit_code == 0

    data = json.loads((tmp_path / "workspaces.json").read_text(encoding="utf-8"))
    renamed = next(ws for ws in data.values() if ws["name"] == "Renamed")
    assert renamed["state"] == {"count": 3, "mode": "ready"}

    removed = isolated_cli_runner.invoke(workspace_cli, ["remove", "Renamed", "--force"])
    assert removed.exit_code == 0
    assert "Workspace 'Renamed' removed successfully" in removed.output

    for command in (
        ["show", "missing"],
        ["update", "missing", "--name", "x"],
        ["remove", "missing", "--force"],
        ["set-state", "missing", "--key", "x", "--value", "y"],
    ):
        result = isolated_cli_runner.invoke(workspace_cli, command)
        assert result.exit_code == 0
        assert "not found" in result.output


def test_workspace_rule_commands(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.workspace.get_config_dir", lambda: tmp_path)
    workspace = Workspace(id="ws1", name="Rules")
    _save_workspace(tmp_path, workspace)

    added = isolated_cli_runner.invoke(
        workspace_cli,
        [
            "add-rule",
            "Rules",
            "--name",
            "Always",
            "--priority",
            "HIGH",
            "--condition",
            '{"type": "always"}',
            "--action",
            "notify",
        ],
    )
    assert added.exit_code == 0
    assert "Rule 'Always' added" in added.output

    data = json.loads((tmp_path / "workspaces.json").read_text(encoding="utf-8"))
    rule = next(iter(data["ws1"]["rules"].values()))
    assert rule["priority"] == RulePriority.HIGH.value
    assert rule["condition"] == {"type": "always"}
    assert rule["action"] == {"type": "notify"}

    invalid = isolated_cli_runner.invoke(
        workspace_cli,
        ["add-rule", "Rules", "--name", "Bad", "--condition", "{bad"],
    )
    assert invalid.exit_code == 0
    assert "Invalid JSON for condition" in invalid.output

    removed = isolated_cli_runner.invoke(workspace_cli, ["remove-rule", "Rules", "Always"])
    assert removed.exit_code == 0
    assert "removed from workspace" in removed.output

    missing_rule = isolated_cli_runner.invoke(
        workspace_cli, ["remove-rule", "Rules", "missing"]
    )
    assert missing_rule.exit_code == 0
    assert "Rule 'missing' not found" in missing_rule.output

    missing_workspace = isolated_cli_runner.invoke(
        workspace_cli, ["add-rule", "missing", "--name", "x"]
    )
    assert missing_workspace.exit_code == 0
    assert "Workspace 'missing' not found" in missing_workspace.output


def test_workspace_show_renders_nodes_rules_inherited_rules_and_state(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.workspace.get_config_dir", lambda: tmp_path)
    workspace = Workspace(id="ws1", name="Detailed", state={"mode": "ready"})
    workspace.add_rule(Rule(id="r1", name="Local", priority=RulePriority.CRITICAL))
    workspace.inherited_rules["ir1"] = Rule(
        id="ir1",
        name="Inherited",
        inherited_from="Parent:r1",
        priority=RulePriority.MEDIUM,
    )
    _save_workspace(tmp_path, workspace)

    result = isolated_cli_runner.invoke(workspace_cli, ["show", "Detailed"])

    assert result.exit_code == 0
    assert "Workspace Rules:" in result.output
    assert "Inherited Rules:" in result.output
    assert "Current State:" in result.output
    assert "mode: ready" in result.output


def test_workspace_init_files_existing_workspace_custom_path(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.workspace.get_config_dir", lambda: tmp_path)
    _save_workspace(tmp_path, Workspace(id="ws1", name="Files"))
    root = tmp_path / "files-root"

    result = isolated_cli_runner.invoke(
        workspace_cli, ["init-files", "Files", "--path", str(root)]
    )

    assert result.exit_code == 0
    assert "Initialized workspace files for 'Files'" in result.output
    assert (root / "memory" / "MEMORY.md").exists()
    data = json.loads((tmp_path / "workspaces.json").read_text(encoding="utf-8"))
    assert data["ws1"]["root_path"] == str(root.resolve())

    missing = isolated_cli_runner.invoke(
        workspace_cli, ["init-files", "missing", "--path", str(tmp_path / "x")]
    )
    assert missing.exit_code == 0
    assert "Workspace 'missing' not found" in missing.output
