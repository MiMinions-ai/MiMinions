"""One-shot prompt CLI for the MiMinions runtime."""

from __future__ import annotations


import click
from .dispatch import attachment_options, submit_task, validate_attachment

from miminions.core.paths import get_config_dir


@click.group()
def prompt_cli() -> None:
    """Prompt commands."""
    pass


@prompt_cli.command("ask")
@click.option("--workspace", "workspace_ref", default="default", show_default=True, help="Workspace id or name.")
@click.option("--session", "session_id", default=None, help="Optional existing session id.")
@click.argument("prompt_parts", nargs=-1, required=True)
@attachment_options
def ask_prompt(workspace_ref: str, session_id: str | None, prompt_parts: tuple[str, ...], attach=False, detach=False) -> None:
    """Send a single prompt to the Minion runtime."""
    user_prompt = " ".join(prompt_parts).strip()
    if not user_prompt:
        raise click.ClickException("Prompt cannot be empty.")

    validate_attachment(attach, detach)
    from miminions.session.store import create_session_id
    from miminions.core.workspace import WorkspaceManager, resolve_workspace
    from miminions.execution.processes import InstanceLock
    from miminions.execution.models import conversation_key
    session_id = (session_id or create_session_id()).strip()
    if not session_id.strip() or "/" in session_id or "\\" in session_id:
        raise click.UsageError("Session ID must be nonempty and contain no path separators.")
    try:
        # Reserve only the workspace identity here; files and model context are built after acknowledgement.
        with InstanceLock(get_config_dir() / "execution-workspace.lock"):
            manager = WorkspaceManager(get_config_dir())
            workspaces = manager.load_workspaces()
            workspace = resolve_workspace(workspaces, workspace_ref)
            if workspace is None:
                workspace = manager.create_workspace(workspace_ref)
                workspaces[workspace.id] = workspace
                manager.save_workspaces(workspaces)
            workspace_ref = workspace.id
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    submit_task("prompt", {"workspace": workspace_ref, "session_id": session_id, "prompt": user_prompt},
                attach=attach, detach=detach, session_key=conversation_key(workspace_ref, session_id), home=get_config_dir())
