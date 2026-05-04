"""Interactive chat CLI — user messages go to the Minion, replies come back."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click

from miminions.agent import create_minion
from miminions.memory.distiller import llm_filter
from miminions.session.store import JsonlSessionStore
from miminions.core.workspace import WorkspaceManager
from miminions.interface.cli.auth import get_config_dir


def _resolve_workspace(manager: Any, workspace_ref: str) -> Any:
    workspaces = manager.load_workspaces()
    if not workspaces:
        return None
    if workspace_ref in workspaces:
        return workspaces[workspace_ref]
    for ws_id, workspace in workspaces.items():
        if str(ws_id) == workspace_ref:
            return workspace
        if str(getattr(workspace, "id", "")) == workspace_ref:
            return workspace
        if str(getattr(workspace, "name", "")) == workspace_ref:
            return workspace
    return None


@click.group()
def chat_cli():
    """Chat commands."""
    pass


@chat_cli.command("start")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.option("--session", "session_id", default=None, help="Optional existing session id.")
def chat_command(workspace_ref: str, session_id: str | None) -> None:
    """Start an interactive chat session powered by the Minion agent."""
    asyncio.run(_chat_loop(workspace_ref, session_id))


async def _chat_loop(workspace_ref: str, session_id: str | None) -> None:
    """Main async chat loop."""
    manager = WorkspaceManager(get_config_dir())
    workspace = _resolve_workspace(manager, workspace_ref)

    if workspace is None:
        raise click.ClickException(f"Workspace not found: {workspace_ref}")

    root_path = getattr(workspace, "root_path", None)
    if not root_path:
        raise click.ClickException("This workspace has no root_path. Run workspace init-files first.")

    root = Path(root_path)
    if not root.exists():
        raise click.ClickException(f"root_path does not exist: {root}")

    store = JsonlSessionStore(root)
    if not session_id:
        session_id = store.create_session_id()

    # Build the agent once — it lives for the entire session.
    system_prompt = llm_filter()["history_summary"]
    minion = create_minion(name="MiMinions", description=system_prompt)

    workspace_name = getattr(workspace, "name", getattr(workspace, "id", "unknown"))
    click.echo(f"Workspace : {workspace_name}  |  Session: {session_id}")
    click.echo("Model     : openai/gpt-oss-20b:free via OpenRouter")
    click.echo("Type 'exit' or 'quit' to end the session.\n")

    # Accumulated pydantic_ai message objects — gives the LLM conversation memory.
    message_history: list[Any] = []

    while True:
        try:
            user_text = input("> ").strip()
        except (EOFError, KeyboardInterrupt):
            click.echo("\nSession ended.")
            break

        if not user_text:
            continue
        if user_text.lower() in {"exit", "quit"}:
            click.echo("Session ended.")
            break

        store.append(session_id, "user", user_text, meta={"source": "cli-chat"})

        try:
            reply = await minion.run(user_text, message_history=message_history)
            # Keep the full message history so the LLM remembers prior turns.
            message_history = minion._last_messages
        except Exception as exc:
            reply = f"[error] {type(exc).__name__}: {exc}"

        store.append(session_id, "assistant", reply, meta={"source": "cli-chat"})
        click.echo(f"\n{reply}\n")