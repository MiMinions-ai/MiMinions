"""Tests for built-in Minion tools."""

import subprocess
import sys
from unittest.mock import patch

import pytest

from miminions.tools.default import cli_run_command


def test_cli_run_command_success():
    """A successful command returns its output and zero exit code."""
    result = cli_run_command(f"{sys.executable} --version")

    assert result["returncode"] == 0
    assert "Python" in result["stdout"]
    assert result["stderr"] == ""


def test_cli_run_command_nonzero_exit():
    """A failed command returns its nonzero exit code and stderr."""
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

        with pytest.raises(TimeoutError, match="timed out after 1 seconds"):
            cli_run_command(f"{sys.executable} --version", timeout=1)
