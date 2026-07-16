"""Tests for built-in Minion tools."""

import subprocess
import sys
from unittest.mock import patch

import pytest

from miminions.tools.default import cli_run_command


def test_cli_run_command_success():
    """A successful command returns its output and zero exit code."""
    with patch("miminions.tools.default.click.confirm", return_value=True):
        result = cli_run_command(f"{sys.executable} --version")

    assert result["returncode"] == 0
    assert "Python" in result["stdout"]
    assert result["stderr"] == ""


def test_cli_run_command_nonzero_exit():
    """A failed command returns its nonzero exit code and stderr."""
    with patch("miminions.tools.default.click.confirm", return_value=True):
        result = cli_run_command(
            f"{sys.executable} --definitely-not-a-python-option"
        )

    assert result["returncode"] != 0
    assert "definitely-not-a-python-option" in result["stderr"]


def test_cli_run_command_rejects_empty_command():
    """An empty command is rejected before creating a subprocess."""
    with pytest.raises(ValueError, match="Command must not be empty"):
        cli_run_command("   ")


def test_cli_run_command_timeout():
    """A subprocess timeout is exposed as a clear timeout error."""
    with patch("miminions.tools.default.subprocess.run") as mock_run:
        mock_run.side_effect = subprocess.TimeoutExpired(["python"], timeout=1)

        with patch("miminions.tools.default.click.confirm", return_value=True):
            with pytest.raises(TimeoutError, match="timed out after 1 seconds"):
                cli_run_command(f"{sys.executable} --version", timeout=1)


def test_cli_run_command_rejects_denied_permission():
    """A declined command never creates a subprocess."""
    command = f"{sys.executable} --version"

    with patch("miminions.tools.default.click.confirm", return_value=False) as confirm:
        with patch("miminions.tools.default.subprocess.run") as mock_run:
            with pytest.raises(PermissionError, match="not approved"):
                cli_run_command(command)

    confirm.assert_called_once_with(f"Execute command: {command}", default=False)
    mock_run.assert_not_called()


def test_cli_run_command_rejects_unavailable_confirmation():
    """An aborted confirmation fails closed without creating a subprocess."""
    with patch("miminions.tools.default.click.confirm", side_effect=EOFError):
        with patch("miminions.tools.default.subprocess.run") as mock_run:
            with pytest.raises(PermissionError, match="not approved"):
                cli_run_command(f"{sys.executable} --version")

    mock_run.assert_not_called()
