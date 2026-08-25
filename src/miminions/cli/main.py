"""
MiMinions CLI - Main command line interface for the MiMinions package.

Help / bare invocation stays cheap: subcommand modules are imported lazily,
and first-run bootstrap only runs when a real subcommand is invoked.
"""

from __future__ import annotations

import importlib
from typing import Any

import click

from miminions import __version__

# (cli name, module, attribute, short help for root --help without importing)
_LAZY_COMMANDS: tuple[tuple[str, str, str, str], ...] = (
    ("auth", "miminions.cli.auth", "auth_cli", "Authentication and configuration."),
    ("agent", "miminions.cli.agent", "agent_cli", "Create and manage agents."),
    ("task", "miminions.cli.task", "task_cli", "Manage tasks."),
    ("knowledge", "miminions.cli.knowledge", "knowledge_cli", "Manage knowledge entries."),
    ("workspace", "miminions.cli.workspace", "workspace_cli", "Manage workspaces."),
    ("execution", "miminions.cli.execution", "execution_cli", "Live execution sessions."),
    ("chat", "miminions.cli.chat", "chat_cli", "Interactive chat sessions."),
    ("gateway", "miminions.cli.gateway", "gateway_cli", "Gateway runtime and channels."),
    ("prompt", "miminions.cli.prompt", "prompt_cli", "One-shot prompts."),
)


class LazyGroup(click.Group):
    """Click group that resolves heavy subcommand modules on first use."""

    def __init__(
        self,
        *args: Any,
        lazy_commands: dict[str, tuple[str, str]] | None = None,
        lazy_helps: dict[str, str] | None = None,
        **kwargs: Any,
    ):
        super().__init__(*args, **kwargs)
        self._lazy_commands = lazy_commands or {}
        self._lazy_helps = lazy_helps or {}

    def list_commands(self, ctx: click.Context) -> list[str]:
        commands = set(super().list_commands(ctx))
        commands.update(self._lazy_commands)
        return sorted(commands)

    def get_command(self, ctx: click.Context, cmd_name: str) -> click.Command | None:
        command = super().get_command(ctx, cmd_name)
        if command is not None:
            return command
        target = self._lazy_commands.get(cmd_name)
        if target is None:
            return None
        module_name, attr_name = target
        module = importlib.import_module(module_name)
        command = getattr(module, attr_name)
        # Cache on the group so later lookups stay cheap.
        self.add_command(command, name=cmd_name)
        return command

    def format_commands(self, ctx: click.Context, formatter: click.HelpFormatter) -> None:
        """List commands using static short help so root --help stays lazy."""
        rows: list[tuple[str, str]] = []
        for name in self.list_commands(ctx):
            if name in self._lazy_commands and name not in self.commands:
                help_text = self._lazy_helps.get(name, "")
            else:
                command = self.get_command(ctx, name)
                if command is None or command.hidden:
                    continue
                help_text = command.get_short_help_str()
            rows.append((name, help_text))
        if not rows:
            return
        with formatter.section("Commands"):
            formatter.write_dl(rows)


def _maybe_bootstrap(ctx: click.Context) -> None:
    """Run first-run setup only for real subcommands (not bare/help)."""
    if ctx.invoked_subcommand is None:
        return
    # Import bootstrap + config path only when needed so `--help` stays light.
    from miminions.core.bootstrap import ensure_default_setup
    from miminions.cli.auth import get_config_dir

    try:
        ensure_default_setup(get_config_dir())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@click.group(
    cls=LazyGroup,
    lazy_commands={name: (module, attr) for name, module, attr, _help in _LAZY_COMMANDS},
    lazy_helps={name: help_text for name, _module, _attr, help_text in _LAZY_COMMANDS},
)
@click.version_option(version=__version__, prog_name="miminions")
@click.pass_context
def cli(ctx: click.Context) -> None:
    """MiMinions CLI - Manage AI agents, tasks, workflows and knowledge."""
    _maybe_bootstrap(ctx)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
