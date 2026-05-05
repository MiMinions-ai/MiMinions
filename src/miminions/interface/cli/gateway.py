from __future__ import annotations

import asyncio
import importlib.util
import logging
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

import click

from miminions.core.gateway import (
    ChannelManager,
    CronJob,
    CronSchedule,
    CronService,
    LocalGatewayRuntime,
    MessageBus,
    SessionManager,
)
from miminions.core.workspace import WorkspaceManager
from miminions.interface.cli.auth import get_config_dir


@dataclass(frozen=True)
class GatewayPaths:
    root: Path
    sessions_path: Path
    cron_store_path: Path


def _resolve_workspace(manager: Any, workspace_ref: str) -> Any | None:
    """Resolve a workspace by key, id, unique id prefix, or exact name."""
    workspaces = manager.load_workspaces()
    if not workspaces:
        return None

    if workspace_ref in workspaces:
        return workspaces[workspace_ref]

    for workspace in workspaces.values():
        workspace_id = getattr(workspace, "id", None)
        if workspace_id is not None and str(workspace_id) == workspace_ref:
            return workspace

    prefix_matches = [
        workspace
        for workspace in workspaces.values()
        if getattr(workspace, "id", None) is not None
        and str(workspace.id).startswith(workspace_ref)
    ]
    if len(prefix_matches) == 1:
        return prefix_matches[0]
    if len(prefix_matches) > 1:
        return None

    for workspace in workspaces.values():
        workspace_name = getattr(workspace, "name", None)
        if workspace_name is not None and str(workspace_name) == workspace_ref:
            return workspace

    return None


def _get_workspace_or_raise(workspace_ref: str) -> Any:
    manager = WorkspaceManager(get_config_dir())
    workspace = _resolve_workspace(manager, workspace_ref)
    if workspace is None:
        raise click.ClickException(f"Workspace not found: {workspace_ref}")

    root_path = getattr(workspace, "root_path", None)
    if not root_path:
        raise click.ClickException(
            "This workspace has no root_path yet. Run workspace init-files first."
        )

    root = Path(root_path).expanduser()
    if not root.exists():
        raise click.ClickException(f"Workspace root_path does not exist: {root}")

    return workspace


def _get_gateway_paths(workspace: Any) -> GatewayPaths:
    root = Path(getattr(workspace, "root_path")).expanduser().resolve()
    return GatewayPaths(
        root=root,
        sessions_path=root / "sessions" / "gateway",
        cron_store_path=root / "data" / "gateway" / "cron" / "jobs.json",
    )


async def _default_cron_handler(job: CronJob) -> str | None:
    logging.getLogger(__name__).info("Cron job requested agent turn: %s", job.name)
    return None


def _build_cron_service(workspace: Any) -> CronService:
    paths = _get_gateway_paths(workspace)
    return CronService(paths.cron_store_path, on_job=_default_cron_handler)


def _format_ms_timestamp(ms: int | None) -> str:
    if not ms:
        return "-"
    return datetime.fromtimestamp(ms / 1000).isoformat(timespec="seconds")


def _parse_iso_datetime_to_ms(value: str) -> int:
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError as exc:
        raise click.BadParameter("Expected ISO datetime, e.g. 2026-05-05T09:00:00") from exc
    return int(parsed.timestamp() * 1000)


def _confirm_or_force(message: str, force: bool) -> None:
    if force:
        return
    click.confirm(message, abort=True)


def _message_preview(message: str, limit: int = 48) -> str:
    collapsed = " ".join(message.split())
    if len(collapsed) <= limit:
        return collapsed
    return collapsed[: limit - 3] + "..."


def _format_schedule(job: CronJob) -> str:
    schedule = job.schedule
    if schedule.kind == "every":
        seconds = int((schedule.every_ms or 0) / 1000)
        return f"every {seconds}s"
    if schedule.kind == "at":
        return f"at {_format_ms_timestamp(schedule.at_ms)}"
    if schedule.kind == "cron":
        suffix = f" ({schedule.tz})" if schedule.tz else ""
        return f"cron {schedule.expr}{suffix}"
    return schedule.kind


def _echo_job_list(jobs: list[CronJob]) -> None:
    if not jobs:
        click.echo("No cron jobs found.")
        return

    click.echo(
        "ID        Name                 Enabled  Schedule              "
        "Next run             Last status  Message"
    )
    click.echo("-" * 112)
    for job in jobs:
        click.echo(
            f"{job.id:<8}  "
            f"{job.name[:20]:<20} "
            f"{str(job.enabled):<7}  "
            f"{_format_schedule(job)[:21]:<21} "
            f"{_format_ms_timestamp(job.state.next_run_at_ms):<20} "
            f"{(job.state.last_status or '-'):<12} "
            f"{_message_preview(job.payload.message)}"
        )


def _validate_name_and_message(name: str, message: str) -> None:
    if not name.strip():
        raise click.BadParameter("name cannot be empty")
    if not message.strip():
        raise click.BadParameter("message cannot be empty")


@click.group()
def gateway_cli() -> None:
    """Manage the MiMinions gateway runtime, scheduled jobs, and gateway sessions."""


@gateway_cli.command("status")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
def gateway_status(workspace_ref: str) -> None:
    """Show gateway status for a workspace."""
    workspace = _get_workspace_or_raise(workspace_ref)
    paths = _get_gateway_paths(workspace)
    cron = _build_cron_service(workspace)

    session_count = (
        len(list(paths.sessions_path.glob("*.jsonl")))
        if paths.sessions_path.exists()
        else 0
    )
    cron_count = cron.status()["jobs"]

    click.echo(f"Workspace name: {getattr(workspace, 'name', '-')}")
    click.echo(f"Workspace ID: {getattr(workspace, 'id', '-')}")
    click.echo(f"Workspace root_path: {paths.root}")
    click.echo(f"Gateway session storage path: {paths.sessions_path}")
    click.echo(f"Cron job storage path: {paths.cron_store_path}")
    click.echo(f"Number of sessions: {session_count}")
    click.echo(f"Number of cron jobs: {cron_count}")


@gateway_cli.command("run")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.option("--no-cron", is_flag=True, help="Start without the cron service.")
@click.option("--log-level", default="INFO", show_default=True, help="Python logging level.")
def gateway_run(workspace_ref: str, no_cron: bool, log_level: str) -> None:
    """Start the local gateway runtime for a workspace."""
    workspace = _get_workspace_or_raise(workspace_ref)
    paths = _get_gateway_paths(workspace)
    logging.basicConfig(level=getattr(logging, log_level.upper(), logging.INFO))

    async def run_until_cancelled() -> None:
        bus = MessageBus()
        channel_manager = ChannelManager(bus)
        cron_service = None if no_cron else _build_cron_service(workspace)
        runtime = LocalGatewayRuntime(channel_manager, cron_service=cron_service)

        click.echo(f"Gateway starting for workspace: {getattr(workspace, 'name', '-')}")
        click.echo(f"Sessions path: {paths.sessions_path}")
        click.echo(f"Cron store: {paths.cron_store_path}")
        click.echo("")

        await runtime.start()
        click.echo("Gateway running.")
        click.echo("Press Ctrl+C to stop.")

        try:
            while True:
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            raise
        finally:
            await runtime.shutdown()

    try:
        asyncio.run(run_until_cancelled())
    except KeyboardInterrupt:
        click.echo("")
        click.echo("Gateway stopped.")


@gateway_cli.group("cron")
def gateway_cron_cli() -> None:
    """Manage gateway cron jobs."""


@gateway_cron_cli.command("list")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.option("--all", "include_disabled", is_flag=True, help="Include disabled jobs.")
def cron_list(workspace_ref: str, include_disabled: bool) -> None:
    """List gateway cron jobs."""
    workspace = _get_workspace_or_raise(workspace_ref)
    cron = _build_cron_service(workspace)
    _echo_job_list(cron.list_jobs(include_disabled=include_disabled))


@gateway_cron_cli.command("add-every")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.option("--name", required=True, help="Job name.")
@click.option("--every-seconds", type=int, default=None, help="Run every N seconds.")
@click.option("--every-minutes", type=int, default=None, help="Run every N minutes.")
@click.option("--every-hours", type=int, default=None, help="Run every N hours.")
@click.option("--message", required=True, help="Message to run.")
def cron_add_every(
    workspace_ref: str,
    name: str,
    every_seconds: int | None,
    every_minutes: int | None,
    every_hours: int | None,
    message: str,
) -> None:
    """Add a recurring interval cron job."""
    _validate_name_and_message(name, message)
    intervals = [
        value
        for value in (every_seconds, every_minutes, every_hours)
        if value is not None
    ]
    if len(intervals) != 1:
        raise click.BadParameter(
            "Specify exactly one of --every-seconds, --every-minutes, or --every-hours."
        )
    interval = intervals[0]
    if interval <= 0:
        raise click.BadParameter("interval must be positive")

    every_ms = 0
    if every_seconds is not None:
        every_ms = every_seconds * 1000
    elif every_minutes is not None:
        every_ms = every_minutes * 60 * 1000
    elif every_hours is not None:
        every_ms = every_hours * 60 * 60 * 1000

    workspace = _get_workspace_or_raise(workspace_ref)
    job = _build_cron_service(workspace).add_job(
        name=name.strip(),
        schedule=CronSchedule(kind="every", every_ms=every_ms),
        message=message.strip(),
    )
    click.echo(f"Added cron job {job.id}: {job.name}")


@gateway_cron_cli.command("add-at")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.option("--name", required=True, help="Job name.")
@click.option(
    "--at",
    "at_value",
    required=True,
    help="ISO datetime. Local time is used if no timezone is included.",
)
@click.option("--message", required=True, help="Message to run.")
def cron_add_at(workspace_ref: str, name: str, at_value: str, message: str) -> None:
    """Add a one-shot cron job."""
    _validate_name_and_message(name, message)
    at_ms = _parse_iso_datetime_to_ms(at_value)
    workspace = _get_workspace_or_raise(workspace_ref)
    job = _build_cron_service(workspace).add_job(
        name=name.strip(),
        schedule=CronSchedule(kind="at", at_ms=at_ms),
        message=message.strip(),
    )
    click.echo(f"Added cron job {job.id}: {job.name}")


@gateway_cron_cli.command("add-cron")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.option("--name", required=True, help="Job name.")
@click.option("--expr", required=True, help="Cron expression.")
@click.option("--tz", default=None, help="Timezone for the cron expression.")
@click.option("--message", required=True, help="Message to run.")
def cron_add_cron(
    workspace_ref: str,
    name: str,
    expr: str,
    tz: str | None,
    message: str,
) -> None:
    """Add a cron-expression job."""
    _validate_name_and_message(name, message)
    if importlib.util.find_spec("croniter") is None:
        raise click.ClickException(
            "Cron expressions require croniter. Install it with: pip install croniter"
        )

    workspace = _get_workspace_or_raise(workspace_ref)
    try:
        job = _build_cron_service(workspace).add_job(
            name=name.strip(),
            schedule=CronSchedule(kind="cron", expr=expr.strip(), tz=tz),
            message=message.strip(),
        )
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Added cron job {job.id}: {job.name}")


@gateway_cron_cli.command("remove")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.argument("job_id")
@click.option("--force", is_flag=True, help="Remove without confirmation.")
def cron_remove(workspace_ref: str, job_id: str, force: bool) -> None:
    """Remove a gateway cron job."""
    workspace = _get_workspace_or_raise(workspace_ref)
    _confirm_or_force(f"Remove cron job {job_id}?", force)
    removed = _build_cron_service(workspace).remove_job(job_id)
    if not removed:
        raise click.ClickException(f"Cron job not found: {job_id}")
    click.echo(f"Removed cron job: {job_id}")


@gateway_cron_cli.command("enable")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.argument("job_id")
def cron_enable(workspace_ref: str, job_id: str) -> None:
    """Enable a gateway cron job."""
    workspace = _get_workspace_or_raise(workspace_ref)
    job = _build_cron_service(workspace).enable_job(job_id, enabled=True)
    if job is None:
        raise click.ClickException(f"Cron job not found: {job_id}")
    click.echo(f"Enabled cron job: {job_id}")


@gateway_cron_cli.command("disable")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.argument("job_id")
def cron_disable(workspace_ref: str, job_id: str) -> None:
    """Disable a gateway cron job."""
    workspace = _get_workspace_or_raise(workspace_ref)
    job = _build_cron_service(workspace).enable_job(job_id, enabled=False)
    if job is None:
        raise click.ClickException(f"Cron job not found: {job_id}")
    click.echo(f"Disabled cron job: {job_id}")


@gateway_cron_cli.command("run")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.argument("job_id")
@click.option("--force", is_flag=True, help="Run even if the job is disabled.")
def cron_run(workspace_ref: str, job_id: str, force: bool) -> None:
    """Run a gateway cron job now."""
    workspace = _get_workspace_or_raise(workspace_ref)
    ran = asyncio.run(_build_cron_service(workspace).run_job(job_id, force=force))
    if not ran:
        raise click.ClickException(f"Cron job not found or disabled: {job_id}")
    click.echo(f"Ran cron job: {job_id}")


@gateway_cli.group("sessions")
def gateway_sessions_cli() -> None:
    """Manage gateway sessions."""


@gateway_sessions_cli.command("list")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.option("--show-path", is_flag=True, help="Show session file paths.")
def sessions_list(workspace_ref: str, show_path: bool) -> None:
    """List gateway sessions."""
    workspace = _get_workspace_or_raise(workspace_ref)
    paths = _get_gateway_paths(workspace)
    if not paths.sessions_path.exists():
        click.echo("No sessions found.")
        return

    sessions = SessionManager(paths.sessions_path).list_sessions()
    if not sessions:
        click.echo("No sessions found.")
        return

    header = "Session key                       Created at                  Updated at"
    if show_path:
        header += "                  Path"
    click.echo(header)
    click.echo("-" * len(header))
    for session in sessions:
        line = (
            f"{str(session.get('key', '-'))[:32]:<33} "
            f"{str(session.get('created_at', '-'))[:27]:<27} "
            f"{str(session.get('updated_at', '-'))[:27]:<27}"
        )
        if show_path:
            line += f" {session.get('path', '-')}"
        click.echo(line)


@gateway_sessions_cli.command("show")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.argument("session_key")
@click.option("--limit", default=20, show_default=True, type=int, help="Recent message limit.")
@click.option("--full", "show_full", is_flag=True, help="Show the full session.")
def sessions_show(
    workspace_ref: str,
    session_key: str,
    limit: int,
    show_full: bool,
) -> None:
    """Show a gateway session."""
    if limit <= 0:
        raise click.BadParameter("limit must be positive")

    workspace = _get_workspace_or_raise(workspace_ref)
    paths = _get_gateway_paths(workspace)
    manager = SessionManager(paths.sessions_path)
    known = {session.get("key") for session in manager.list_sessions()}
    if session_key not in known:
        raise click.ClickException(f"Session not found: {session_key}")

    session = manager.get_or_create(session_key)
    messages = session.messages if show_full else session.messages[-limit:]
    click.echo(f"Session: {session.key}")
    click.echo("")
    if not messages:
        click.echo("No messages found.")
        return
    for message in messages:
        role = message.get("role", "unknown")
        content = message.get("content", "")
        click.echo(f"[{role}] {content}")


@gateway_sessions_cli.command("delete")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.argument("session_key")
@click.option("--force", is_flag=True, help="Delete without confirmation.")
def sessions_delete(workspace_ref: str, session_key: str, force: bool) -> None:
    """Delete a gateway session."""
    workspace = _get_workspace_or_raise(workspace_ref)
    paths = _get_gateway_paths(workspace)
    manager = SessionManager(paths.sessions_path)
    known = {session.get("key") for session in manager.list_sessions()}
    if session_key not in known:
        raise click.ClickException(f"Session not found: {session_key}")

    _confirm_or_force(f"Delete session {session_key}?", force)
    deleted = manager.delete(session_key)
    if not deleted:
        raise click.ClickException(f"Session not found: {session_key}")
    click.echo(f"Deleted session: {session_key}")
