"""Manage the persistent local execution instance."""

import json

import click

from miminions.execution import ExecutionService


@click.group("instance")
def instance_cli():
    """Manage the local execution instance."""


@instance_cli.command("start")
def start_instance():
    """Start the execution instance if it is not already running."""
    try:
        service = ExecutionService()
        service.ensure_instance(on_start=lambda message: click.echo(message, err=True))
        click.echo(f"Execution instance running (PID {service.status()['pid']}).")
    except (ValueError, OSError) as exc:
        raise click.ClickException(str(exc)) from exc


@instance_cli.command("status")
@click.option("--json", "as_json", is_flag=True)
def instance_status(as_json):
    """Show supervisor health and configuration."""
    service = ExecutionService()
    state = service.status()
    if as_json:
        click.echo(json.dumps(state, indent=2))
    else:
        status = "draining" if state.get("healthy") and state.get("stopping") else "running" if state.get("healthy") else "stopped"
        click.echo(f"Execution instance: {status} (PID {state.get('pid', '-')}, concurrency {state.get('max_concurrency', 4)})")


@instance_cli.command("stop")
@click.option("--cancel", is_flag=True, help="Cancel queued and active tasks instead of draining them.")
def stop_instance(cancel):
    """Request shutdown after accepted work finishes."""
    service = ExecutionService()
    if not service.status().get("healthy"):
        click.echo("Execution instance is stopped.")
        return
    service.stop(cancel=cancel)
    click.echo("Execution instance cancellation requested." if cancel else "Execution instance draining accepted work.")
