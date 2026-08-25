"""
Integration tests for the miminions init command.
"""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from miminions.cli.main import cli


def _workspace_root(config_dir: Path, config: dict) -> Path:
    return config_dir / "workspaces" / f"ws_{config['default_workspace']}"


def test_init_creates_default_setup(temp_config_dir):
    runner = CliRunner()

    with patch("miminions.core.paths.get_config_dir", return_value=temp_config_dir):
        result = runner.invoke(cli, ["init"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Bootstrap initialization complete." in result.output, f"expect init command reports successful bootstrap initialization path completion as 'Bootstrap initialization complete.', got {result.output}"

    config = json.loads((temp_config_dir / "config.json").read_text())
    root = _workspace_root(temp_config_dir, config)

    default_workspace_id = config["default_workspace"]
    assert default_workspace_id, f"expect init sets default_workspace as True, got {default_workspace_id}"
    default_agent_name = config["default_agent"]
    assert default_agent_name, f"expect init sets default_agent as True, got {default_agent_name}"
    agents_file_exists = (root / "prompt" / "AGENTS.md").exists()
    assert agents_file_exists, f"expect init creates prompt/AGENTS.md as True, got {agents_file_exists}"
    user_file_exists = (root / "prompt" / "USER.md").exists()
    assert user_file_exists, f"expect init creates prompt/USER.md as True, got {user_file_exists}"
    tools_file_exists = (root / "prompt" / "TOOLS.md").exists()
    assert tools_file_exists, f"expect init creates prompt/TOOLS.md as True, got {tools_file_exists}"
    identity_file_exists = (root / "prompt" / "IDENTITY.md").exists()
    assert identity_file_exists, f"expect init creates prompt/IDENTITY.md as True, got {identity_file_exists}"


def test_init_force_repairs_missing_templates(temp_config_dir):
    runner = CliRunner()

    with patch("miminions.core.paths.get_config_dir", return_value=temp_config_dir):
        first = runner.invoke(cli, ["init"])
        assert first.exit_code == 0, f"expect first exit code 0, got {first.exit_code} with output: {first.output}"

    config = json.loads((temp_config_dir / "config.json").read_text())
    root = _workspace_root(temp_config_dir, config)

    tools_md = root / "prompt" / "TOOLS.md"
    user_md = root / "prompt" / "USER.md"

    user_md.write_text("# customized by user\n")
    tools_md.unlink()

    with patch("miminions.core.paths.get_config_dir", return_value=temp_config_dir):
        result = runner.invoke(cli, ["init", "--force"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Bootstrap repair complete." in result.output, f"expect init --force command reports bootstrap repair path completion as 'Bootstrap repair complete.', got {result.output}"
    tools_file_exists = tools_md.exists()
    assert tools_file_exists, f"expect init --force recreates missing TOOLS.md as True, got {tools_file_exists}"
    user_content = user_md.read_text()
    assert user_content == "# customized by user\n", f"expect init --force preserves existing customized USER.md content while repairing missing templates as '# customized by user\n', got {user_content}"
