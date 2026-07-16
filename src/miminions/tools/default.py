"""Built-in tools available to every Minion."""

import shlex
import subprocess
import sys
from typing import Any, Dict

import click


CLI_RUN_COMMAND_NAME = "cli_run_command"
CLI_RUN_COMMAND_DESCRIPTION = (
    "Execute an approved CLI command without a shell and return stdout, stderr, "
    "and return code"
)


def cli_run_command(command: str, timeout: int = 30) -> Dict[str, Any]:
    """Ask for approval, then run a command with subprocess using shell=False."""
    if not command or not command.strip():
        raise ValueError("Command must not be empty")
    if timeout <= 0:
        raise ValueError("Timeout must be greater than zero")

    try:
        args = shlex.split(command, posix=(sys.platform != "win32"))
    except ValueError as exc:
        raise ValueError(f"Could not parse command: {exc}") from exc

    if not args:
        raise ValueError("Command must not be empty")

    try:
        approved = click.confirm(
            f"Execute command: {command}",
            default=False,
        )
    except (click.Abort, EOFError) as exc:
        raise PermissionError("Command execution was not approved") from exc

    if not approved:
        raise PermissionError("Command execution was not approved")

    try:
        completed = subprocess.run(
            args,
            shell=False,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as exc:
        raise TimeoutError(f"Command timed out after {timeout} seconds") from exc

    return {
        "command": command,
        "returncode": completed.returncode,
        "stdout": completed.stdout,
        "stderr": completed.stderr,
    }
