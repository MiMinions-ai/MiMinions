"""Smoke tests for the registered CLI command groups."""

from unittest.mock import patch

from click.testing import CliRunner

from miminions.cli.agent import agent_cli
from miminions.cli.auth import auth_cli
from miminions.cli.main import cli


def test_basic_cli_help_and_auth_status(tmp_path):
    """Root help and auth status should work with isolated config."""
    runner = CliRunner()
    config_dir = tmp_path / ".miminions"
    config_dir.mkdir()

    result = runner.invoke(cli, ["--help"])
    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "MiMinions CLI" in result.output, f"expect cli help output includes product heading text for root command as 'MiMinions CLI', got {result.output}"

    with (
        patch("miminions.core.paths.get_config_dir", return_value=config_dir),
        patch("miminions.cli.auth.get_config_dir", return_value=config_dir),
        patch("miminions.cli.config.get_config_dir", return_value=config_dir),
    ):
        result = runner.invoke(cli, ["auth", "status"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Not signed in" in result.output, f"expect auth status command reports not-signed-in state when no credentials exist as 'Not signed in', got {result.output}"


def test_auth_signin_persists_auth_data():
    """Signin should report success and save auth data."""
    runner = CliRunner()

    with patch("miminions.cli.auth.save_auth_data") as mock_save:
        result = runner.invoke(auth_cli, ["signin", "--username", "testuser", "--password", "testpass"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Successfully signed in as testuser" in result.output, f"expect signin command confirms successful authentication for provided username as 'Successfully signed in as testuser', got {result.output}"
    mock_save.assert_called_once()


def test_agent_list_does_not_require_auth_and_empty_state():
    """Agent list should run without auth and show empty inventory state."""
    runner = CliRunner()

    with patch("miminions.cli.agent.load_agents", return_value={}):
        result = runner.invoke(agent_cli, ["list"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "No agents configured" in result.output, f"expect agent list command reports empty agent inventory when config has no agents as 'No agents configured', got {result.output}"

    with (
        patch("miminions.cli.agent.load_agents", return_value={}),
    ):
        result = runner.invoke(agent_cli, ["list"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "No agents configured" in result.output, f"expect agent list command reports empty agent inventory when config has no agents as 'No agents configured', got {result.output}"