"""
Integration tests for miminions config get/set commands.
"""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from miminions.cli.main import cli
from miminions.core.workspace import WorkspaceManager


def _load_json(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_config_get_returns_existing_default_workspace(temp_config_dir):
    runner = CliRunner()

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        first = runner.invoke(cli, ["init"])
        assert first.exit_code == 0, f"expect first exit code 0, got {first.exit_code} with output: {first.output}"

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.config.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["config", "get", "default_workspace"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    config = _load_json(temp_config_dir / "config.json")
    output_value = result.output.strip()
    assert output_value == config["default_workspace"], f"expect config get default_workspace returns persisted default workspace id '{config['default_workspace']}' from config file, got {output_value}"


def test_config_set_default_workspace_resolves_name_to_id(temp_config_dir):
    runner = CliRunner()

    manager = WorkspaceManager(temp_config_dir)
    workspace = manager.create_workspace("project-alpha", "")
    manager.save_workspaces({workspace.id: workspace})

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.config.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["config", "set", "default_workspace", "project-alpha"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    config = _load_json(temp_config_dir / "config.json")
    assert config["default_workspace"] == workspace.id, f"expect config set default_workspace resolves workspace name to workspace id '{workspace.id}' before persistence, got {config['default_workspace']}"


def test_config_set_default_agent_requires_existing_agent(temp_config_dir):
    runner = CliRunner()
    agents_file = temp_config_dir / "agents.json"
    agents_file.write_text(json.dumps({"researcher": {"name": "Researcher"}}), encoding="utf-8")

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.config.get_config_dir", return_value=temp_config_dir):
            ok = runner.invoke(cli, ["config", "set", "default_agent", "researcher"])
            fail = runner.invoke(cli, ["config", "set", "default_agent", "missing"])

    assert ok.exit_code == 0, f"expect cli ok exit code 0, got {ok.exit_code} with output: {ok.output}"
    assert fail.exit_code != 0, f"expect cli error exit code != 0, got {fail.exit_code} with output: {fail.output}"
    assert "Agent not found: missing" in fail.output, f"expect config set default_agent rejects unknown agent id and reports exact error 'Agent not found: missing', got {fail.output}"

    config = _load_json(temp_config_dir / "config.json")
    assert config["default_agent"] == "researcher", f"expect successful default_agent update keeps previous valid agent value 'researcher' in config after rejected update attempt, got {config['default_agent']}"


def test_config_rejects_unknown_key(temp_config_dir):
    runner = CliRunner()

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.config.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["config", "set", "public_access", "true"])

    assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
    assert "Unsupported key 'public_access'" in result.output, f"expect \"Unsupported key 'public_access'\" in result.output, got {result.output}"
