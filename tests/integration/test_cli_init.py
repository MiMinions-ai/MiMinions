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

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        result = runner.invoke(cli, ["init"])

    assert result.exit_code == 0
    assert "Bootstrap initialization complete." in result.output

    config = json.loads((temp_config_dir / "config.json").read_text())
    root = _workspace_root(temp_config_dir, config)

    assert config["default_workspace"]
    assert config["default_agent"]
    assert (root / "prompt" / "AGENTS.md").exists()
    assert (root / "prompt" / "USER.md").exists()
    assert (root / "prompt" / "TOOLS.md").exists()
    assert (root / "prompt" / "IDENTITY.md").exists()


def test_init_force_repairs_missing_templates(temp_config_dir):
    runner = CliRunner()

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        first = runner.invoke(cli, ["init"])
        assert first.exit_code == 0

    config = json.loads((temp_config_dir / "config.json").read_text())
    root = _workspace_root(temp_config_dir, config)

    tools_md = root / "prompt" / "TOOLS.md"
    user_md = root / "prompt" / "USER.md"

    user_md.write_text("# customized by user\n")
    tools_md.unlink()

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        result = runner.invoke(cli, ["init", "--force"])

    assert result.exit_code == 0
    assert "Bootstrap repair complete." in result.output
    assert tools_md.exists()
    assert user_md.read_text() == "# customized by user\n"
