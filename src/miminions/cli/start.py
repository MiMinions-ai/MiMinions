"""Top-level MiMinions startup command."""

from __future__ import annotations

import asyncio
import subprocess
import sys
from pathlib import Path

import click

from miminions.cli.chat import _chat_loop, _resolve_start_workspace


def _start_gateway_background(workspace_id: str, root: Path) -> int:
    """Start the local gateway runtime detached from the current terminal."""
    gateway_dir = root / "data" / "gateway"
    gateway_dir.mkdir(parents=True, exist_ok=True)
    log_path = gateway_dir / "server.log"
    pid_path = gateway_dir / "server.pid"

    log_file = log_path.open("a", encoding="utf-8")
    try:
        process = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "miminions",
                "gateway",
                "run",
                "--workspace",
                workspace_id,
            ],
            stdout=log_file,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            shell=False,
            close_fds=True,
        )
    finally:
        log_file.close()

    pid_path.write_text(str(process.pid), encoding="utf-8")
    return process.pid


@click.command("start")
@click.option(
    "--session-id",
    "--session",
    "session_id",
    default=None,
    help="Resume an existing session id.",
)
@click.option("--agent", "agent_ref", default=None, help="Agent id or name.")
@click.option(
    "--workspace",
    "workspace_ref",
    default=None,
    help="Workspace id, name, or existing path.",
)
@click.option(
    "--background/--no-background",
    default=False,
    help="Start the gateway runtime in the background instead of opening chat.",
)
def start_cli(
    session_id: str | None,
    agent_ref: str | None,
    workspace_ref: str | None,
    background: bool,
) -> None:
    """Initialize MiMinions and start chat or the local gateway runtime."""
    if background:
        workspace, root = _resolve_start_workspace(workspace_ref)
        workspace_id = getattr(workspace, "id")
        workspace_name = getattr(workspace, "name", workspace_id)
        pid = _start_gateway_background(workspace_id, root)
        log_path = root / "data" / "gateway" / "server.log"

        click.echo(f"Workspace : {workspace_name}")
        click.echo(f"Workspace ID: {workspace_id}")
        click.echo(f"Gateway PID : {pid}")
        click.echo(f"Log path    : {log_path}")
        return

    asyncio.run(
        _chat_loop(
            workspace_ref,
            session_id,
            agent_ref=agent_ref,
            use_start_defaults=True,
            warn_missing_session=True,
        )
    )
