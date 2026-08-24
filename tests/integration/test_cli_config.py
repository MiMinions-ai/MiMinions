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
        assert first.exit_code == 0, f"expect first.exit_code == 0, got {first.exit_code == 0}"

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.config.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["config", "get", "default_workspace"])

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"
    config = _load_json(temp_config_dir / "config.json")
    assert result.output.strip() == config["default_workspace"], f"expect result.output.strip() == config['default_workspace'], got {result.output.strip() == config['default_workspace']}"


def test_config_set_default_workspace_resolves_name_to_id(temp_config_dir):
    runner = CliRunner()

    manager = WorkspaceManager(temp_config_dir)
    workspace = manager.create_workspace("project-alpha", "")
    manager.save_workspaces({workspace.id: workspace})

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.config.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["config", "set", "default_workspace", "project-alpha"])

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"
    config = _load_json(temp_config_dir / "config.json")
    assert config["default_workspace"] == workspace.id, f"expect config['default_workspace'] == workspace.id, got {config['default_workspace'] == workspace.id}"


def test_config_set_default_agent_requires_existing_agent(temp_config_dir):
    runner = CliRunner()
    agents_file = temp_config_dir / "agents.json"
    agents_file.write_text(json.dumps({"researcher": {"name": "Researcher"}}), encoding="utf-8")

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.config.get_config_dir", return_value=temp_config_dir):
            ok = runner.invoke(cli, ["config", "set", "default_agent", "researcher"])
            fail = runner.invoke(cli, ["config", "set", "default_agent", "missing"])

    assert ok.exit_code == 0, f"expect ok.exit_code == 0, got {ok.exit_code == 0}"
    assert fail.exit_code != 0, f"expect fail.exit_code != 0, got {fail.exit_code != 0}"
    assert "Agent not found: missing" in fail.output, f"expect 'Agent not found: missing' in fail.output, got {'Agent not found: missing' in fail.output}"

    config = _load_json(temp_config_dir / "config.json")
    assert config["default_agent"] == "researcher", f"expect config['default_agent'] == 'researcher', got {config['default_agent'] == 'researcher'}"


def test_config_rejects_unknown_key(temp_config_dir):
    runner = CliRunner()

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.config.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["config", "set", "public_access", "true"])

    assert result.exit_code != 0, f"expect result.exit_code != 0, got {result.exit_code != 0}"
    assert "Unsupported key 'public_access'" in result.output, f"expect \"Unsupported key 'public_access'\" in result.output, got {"Unsupported key 'public_access'" in result.output}"
