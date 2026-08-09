"""Built-in tools available to every Minion."""

from dataclasses import dataclass
from enum import Enum
import shlex
import subprocess
import sys
import time
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

import click


CLI_RUN_COMMAND_NAME = "cli_run_command"
CLI_RUN_COMMAND_DESCRIPTION = (
    "Execute an approved CLI command without a shell and return stdout, stderr, "
    "and return code"
)


class PermissionDecision(str, Enum):
    """Possible outcomes when evaluating permission to execute a command."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


CommandPrefix = Tuple[str, ...]


class _TimedCommandResult(dict):
    """Dictionary result carrying subprocess-only timing for the tool runner."""

    def __init__(self, *args: Any, execution_time_ms: float, **kwargs: Any) -> None:
        super().__init__(*args, **kwargs)
        self.execution_time_ms = execution_time_ms


@dataclass(frozen=True)
class CommandPermissionPolicy:
    """Immutable allow, deny, and prompt policy for parsed command arguments."""

    allow_prefixes: Tuple[CommandPrefix, ...] = ()
    deny_prefixes: Tuple[CommandPrefix, ...] = ()
    default: PermissionDecision = PermissionDecision.ASK

    def __init__(
        self,
        allow_prefixes: Iterable[Sequence[str]] = (),
        deny_prefixes: Iterable[Sequence[str]] = (),
        default: PermissionDecision = PermissionDecision.ASK,
    ) -> None:
        object.__setattr__(
            self,
            "allow_prefixes",
            self._validate_prefixes(allow_prefixes, "allow_prefixes"),
        )
        object.__setattr__(
            self,
            "deny_prefixes",
            self._validate_prefixes(deny_prefixes, "deny_prefixes"),
        )
        if not isinstance(default, PermissionDecision):
            raise TypeError("default must be a PermissionDecision")
        object.__setattr__(self, "default", default)

    @staticmethod
    def _validate_prefixes(
        prefixes: Iterable[Sequence[str]],
        name: str,
    ) -> Tuple[CommandPrefix, ...]:
        try:
            normalized = tuple(tuple(prefix) for prefix in prefixes)
        except TypeError as exc:
            raise TypeError(f"{name} must be an iterable of argument sequences") from exc

        for prefix in normalized:
            if not prefix:
                raise ValueError(f"{name} must not contain an empty prefix")
            if any(not isinstance(argument, str) or not argument for argument in prefix):
                raise ValueError(
                    f"{name} prefixes must contain only non-empty strings"
                )
        return normalized

    @staticmethod
    def _matches(args: Sequence[str], prefix: CommandPrefix) -> bool:
        return len(args) >= len(prefix) and tuple(args[:len(prefix)]) == prefix

    def evaluate(self, args: Sequence[str]) -> PermissionDecision:
        """Return the permission decision for already-parsed command arguments."""
        if not args:
            raise ValueError("Command arguments must not be empty")
        if any(not isinstance(argument, str) or not argument for argument in args):
            raise ValueError("Command arguments must contain only non-empty strings")

        if any(self._matches(args, prefix) for prefix in self.deny_prefixes):
            return PermissionDecision.DENY
        if any(self._matches(args, prefix) for prefix in self.allow_prefixes):
            return PermissionDecision.ALLOW
        return self.default


def cli_run_command(
    command: str,
    timeout: int = 30,
    policy: Optional[CommandPermissionPolicy] = None,
) -> Dict[str, Any]:
    """Run a command without a shell after applying a permission policy."""
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

    active_policy = policy if policy is not None else CommandPermissionPolicy()
    if not isinstance(active_policy, CommandPermissionPolicy):
        raise TypeError("policy must be a CommandPermissionPolicy")
    decision = active_policy.evaluate(args)

    if decision is PermissionDecision.DENY:
        raise PermissionError("Command execution was not approved")
    if decision is PermissionDecision.ASK:
        try:
            approved = click.confirm(
                f"Execute command: {command}",
                default=False,
            )
        except (click.Abort, EOFError) as exc:
            raise PermissionError("Command execution was not approved") from exc

        if not approved:
            raise PermissionError("Command execution was not approved")

    execution_started = time.perf_counter()
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
    execution_time_ms = (time.perf_counter() - execution_started) * 1000

    return _TimedCommandResult(
        {
            "command": command,
            "returncode": completed.returncode,
            "stdout": completed.stdout,
            "stderr": completed.stderr,
        },
        execution_time_ms=execution_time_ms,
    )


def cli_run_command_tool(command: str, timeout: int = 30) -> Dict[str, Any]:
    """Agent-facing command tool that always uses the default permission policy."""
    return cli_run_command(command=command, timeout=timeout)
