"""Tests for built-in Minion tools."""

import subprocess
import shlex
import sys
from unittest.mock import patch

import pytest

from miminions.tools.default import (
    CommandPermissionPolicy,
    PermissionDecision,
    cli_run_command,
)


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


def test_allow_prefix_bypasses_confirmation():
    """An allowed argument prefix executes without asking for confirmation."""
    command = f"{sys.executable} --version"
    args = shlex.split(command, posix=(sys.platform != "win32"))
    policy = CommandPermissionPolicy(allow_prefixes=[args])

    with patch("miminions.tools.default.click.confirm") as confirm:
        result = cli_run_command(command, policy=policy)

    assert result["returncode"] == 0
    confirm.assert_not_called()


def test_deny_prefix_blocks_without_confirmation_or_subprocess():
    """A denied argument prefix fails immediately without prompting or running."""
    command = f"{sys.executable} --version"
    args = shlex.split(command, posix=(sys.platform != "win32"))
    policy = CommandPermissionPolicy(deny_prefixes=[args[:1]])

    with patch("miminions.tools.default.click.confirm") as confirm:
        with patch("miminions.tools.default.subprocess.run") as mock_run:
            with pytest.raises(PermissionError, match="not approved"):
                cli_run_command(command, policy=policy)

    confirm.assert_not_called()
    mock_run.assert_not_called()


def test_unmatched_command_uses_default_ask():
    """An unmatched command prompts when the policy defaults to ask."""
    command = f"{sys.executable} --version"
    policy = CommandPermissionPolicy(allow_prefixes=[("another-command",)])

    with patch("miminions.tools.default.click.confirm", return_value=True) as confirm:
        cli_run_command(command, policy=policy)

    confirm.assert_called_once_with(f"Execute command: {command}", default=False)


def test_deny_prefix_takes_precedence_over_allow_prefix():
    """Deny wins when allow and deny rules both match."""
    args = (sys.executable, "--version")
    policy = CommandPermissionPolicy(
        allow_prefixes=[(sys.executable,)],
        deny_prefixes=[args],
    )

    assert policy.evaluate(args) is PermissionDecision.DENY


def test_argument_prefix_matching_is_exact_and_ordered():
    """A specific argument prefix does not match different arguments."""
    policy = CommandPermissionPolicy(
        allow_prefixes=[("python", "--version")],
        default=PermissionDecision.DENY,
    )

    assert policy.evaluate(("python", "--version")) is PermissionDecision.ALLOW
    assert policy.evaluate(("python", "--version", "extra")) is PermissionDecision.ALLOW
    assert policy.evaluate(("python", "--help")) is PermissionDecision.DENY


@pytest.mark.parametrize(
    ("decision", "should_run"),
    [
        (PermissionDecision.ALLOW, True),
        (PermissionDecision.DENY, False),
    ],
)
def test_explicit_default_decisions(decision, should_run):
    """Policies can allow or deny commands that do not match any rule."""
    command = f"{sys.executable} --version"
    policy = CommandPermissionPolicy(default=decision)

    with patch("miminions.tools.default.click.confirm") as confirm:
        with patch("miminions.tools.default.subprocess.run") as mock_run:
            mock_run.return_value.returncode = 0
            mock_run.return_value.stdout = ""
            mock_run.return_value.stderr = ""
            if should_run:
                cli_run_command(command, policy=policy)
            else:
                with pytest.raises(PermissionError, match="not approved"):
                    cli_run_command(command, policy=policy)

    confirm.assert_not_called()
    assert mock_run.called is should_run


@pytest.mark.parametrize(
    "kwargs",
    [
        {"allow_prefixes": [()]},
        {"deny_prefixes": [("",)]},
        {"allow_prefixes": [(None,)]},
    ],
)
def test_invalid_permission_prefixes_are_rejected(kwargs):
    """Empty and non-string rule arguments are invalid."""
    with pytest.raises(ValueError):
        CommandPermissionPolicy(**kwargs)


def test_command_result_reports_subprocess_only_timing():
    """Permission prompt time is excluded from the reported tool duration."""
    completed = subprocess.CompletedProcess(
        args=[sys.executable, "--version"],
        returncode=0,
        stdout="Python test\n",
        stderr="",
    )

    with patch("miminions.tools.default.click.confirm", return_value=True):
        with patch("miminions.tools.default.subprocess.run", return_value=completed):
            with patch(
                "miminions.tools.default.time.perf_counter",
                side_effect=[10.0, 10.025],
            ):
                result = cli_run_command(f"{sys.executable} --version")

    assert result.execution_time_ms == pytest.approx(25.0)
    assert "execution_time_ms" not in result
