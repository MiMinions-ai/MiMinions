from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import click

from miminions.agent.context_builder import ContextBuilder
from miminions.session.store import JsonlSessionStore
from miminions.core.workspace import WorkspaceManager
from miminions.interface.cli.auth import get_config_dir


def _resolve_workspace(manager: Any, workspace_ref: str) -> Any:
    """Resolve a workspace by id or name using WorkspaceManager.load_workspaces()."""
    workspaces = manager.load_workspaces()

    if not workspaces:
        return None

    # Ttry exact dict key match
    if workspace_ref in workspaces:
        return workspaces[workspace_ref]

    # Try matching against workspace.id or workspace.name
    for workspace_id, workspace in workspaces.items():
        if str(workspace_id) == workspace_ref:
            return workspace

        if getattr(workspace, "id", None) is not None and str(workspace.id) == workspace_ref:
            return workspace

        if getattr(workspace, "name", None) is not None and str(workspace.name) == workspace_ref:
            return workspace

    return None


def _save_manager(manager: Any) -> None:
    """Persist manager state if a save-like method exists."""
    for method_name in ("save", "save_workspaces", "persist"):
        if hasattr(manager, method_name):
            getattr(manager, method_name)()
            return


def _default_agent_reply(
    user_text: str,
    context: str,
    workspace: Any,
    session_id: str,
) -> str:
    """Fallback reply used until the real agent hook is wired in."""
    workspace_name = getattr(workspace, "name", None) or getattr(workspace, "id", "unknown")
    preview = context[:500].strip()

    return (
        f"[demo-reply] workspace={workspace_name} session={session_id}\n\n"
        f"You said: {user_text}\n\n"
        f"Context preview:\n{preview}"
    )


def _run_agent(
    user_text: str,
    context: str,
    workspace: Any,
    session_id: str,
) -> str:
    """Run the agent for one user message.

    Current behavior:
    1. If the workspace has a callable 'chat_handler', use it.
    2. Otherwise fall back to a demo reply.

    This keeps the CLI usable now while letting you wire in the real
    agent implementation later.
    """
    chat_handler = getattr(workspace, "chat_handler", None)
    if callable(chat_handler):
        return str(
            chat_handler(
                user_text=user_text,
                context=context,
                workspace=workspace,
                session_id=session_id,
            )
        )

    return _default_agent_reply(user_text, context, workspace, session_id)  

@click.group()
def chat_cli():
    """Chat commands."""
    pass

@chat_cli.command("start")
@click.option(
    "--workspace",
    "workspace_ref",
    required=True,
    help="Workspace id or name.",
)
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Optional existing session id.",
)
def chat_command(workspace_ref: str, session_id: str | None) -> None:
    """Start an interactive chat session for a workspace."""
    manager = WorkspaceManager(get_config_dir())
    workspace = _resolve_workspace(manager, workspace_ref)

    if workspace is None:
        raise click.ClickException(f"Workspace not found: {workspace_ref}")

    root_path = getattr(workspace, "root_path", None)
    if not root_path:
        raise click.ClickException(
            "This workspace has no root_path yet. Run workspace init-files first."
        )

    root = Path(root_path)
    if not root.exists():
        raise click.ClickException(f"Workspace root_path does not exist: {root}")

    context = ContextBuilder().build(workspace, root)
    store = JsonlSessionStore(root)

    if not session_id:
        session_id = store.create_session_id()

    click.echo(f"Workspace: {getattr(workspace, 'name', getattr(workspace, 'id', 'unknown'))}")
    click.echo(f"Session: {session_id}")
    click.echo("Type 'exit' or 'quit' to stop.")
    click.echo("")

    while True:
        try:
            user_text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nExiting chat.")
            break

        if not user_text:
            continue

        if user_text.lower() in {"exit", "quit"}:
            click.echo("Exiting chat.")
            break

        store.append(
            session_id,
            "user",
            user_text,
            meta={"source": "cli-chat"},
        )

        reply = _run_agent(
            user_text=user_text,
            context=context,
            workspace=workspace,
            session_id=session_id,
        )

        store.append(
            session_id,
            "assistant",
            reply,
            meta={"source": "cli-chat"},
        )

        click.echo("")
        click.echo(reply)
        click.echo("")