"""Async chat CLI — talks to the live OpenRouter LLM via pydantic_ai."""

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


# ---------------------------------------------------------------------------
# Workspace helpers (unchanged)
# ---------------------------------------------------------------------------


def _resolve_workspace(manager: Any, workspace_ref: str) -> Any:
    workspaces = manager.load_workspaces()
    if not workspaces:
        return None
    if workspace_ref in workspaces:
        return workspaces[workspace_ref]
    for workspace_id, workspace in workspaces.items():
        if str(workspace_id) == workspace_ref:
            return workspace
        if getattr(workspace, "id", None) is not None and str(workspace.id) == workspace_ref:
            return workspace
        if getattr(workspace, "name", None) is not None and str(workspace.name) == workspace_ref:
            return workspace
    return None


# ---------------------------------------------------------------------------
# Agent runner
# ---------------------------------------------------------------------------


async def _run_agent(user_text: str, message_history: list[Any]) -> str:
    """Run one turn of the LLM agent and return the reply text."""
    # Pull the base identity prompt from the stub distiller.
    stub = llm_filter()
    system_desc = stub.get("history_summary", "You are MiMinions, a helpful AI assistant.")

    minion = create_minion(name="MiMinions", description=system_desc)

    # --- Register tools the LLM can call ---
    def list_registered_tools() -> list[str]:
        """Return the names of all tools registered on this agent."""
        return minion.list_tools()

    minion.register_tool(
        name="list_registered_tools",
        description="List all tool names currently registered on the agent.",
        func=list_registered_tools,
    )

    pydantic_agent = minion.get_pydantic_ai_agent()

    try:
        result = await pydantic_agent.run(
            user_text,
            message_history=message_history or None,
        )
        return result.output if hasattr(result, "output") else str(result.data)
    except Exception as exc:
        error_type = type(exc).__name__
        click.echo(f"\n[agent-error] {error_type}: {exc}", err=True)
        return (
            f"[agent-error] {error_type} — check your OPENROUTER_API_KEY and try again."
        )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


@click.group()
def chat_cli():
    """Chat commands."""
    pass


@chat_cli.command("start")
@click.option("--workspace", "workspace_ref", required=True, help="Workspace id or name.")
@click.option("--session", "session_id", default=None, help="Optional existing session id.")
def chat_command(workspace_ref: str, session_id: str | None) -> None:
    """Start an interactive chat session (LLM-powered via OpenRouter)."""
    asyncio.run(_async_chat(workspace_ref, session_id))


async def _async_chat(workspace_ref: str, session_id: str | None) -> None:
    manager = WorkspaceManager(get_config_dir())
    workspace = _resolve_workspace(manager, workspace_ref)

    if workspace is None:
        raise click.ClickException(f"Workspace not found: {workspace_ref}")

    root_path = getattr(workspace, "root_path", None)
    if not root_path:
        raise click.ClickException("This workspace has no root_path. Run workspace init-files first.")

    root = Path(root_path)
    if not root.exists():
        raise click.ClickException(f"Workspace root_path does not exist: {root}")

    store = JsonlSessionStore(root)
    if not session_id:
        session_id = store.create_session_id()

    workspace_name = getattr(workspace, "name", getattr(workspace, "id", "unknown"))
    click.echo(f"Workspace : {workspace_name}")
    click.echo(f"Session   : {session_id}")
    click.echo("Model     : openai/gpt-oss-20b:free (OpenRouter)")
    click.echo("Type 'exit' or 'quit' to stop.")
    click.echo("")

    message_history: list[Any] = []

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

        store.append(session_id, "user", user_text, meta={"source": "cli-chat"})
        click.echo("  (thinking…)")

        reply = await _run_agent(user_text, message_history)

        store.append(session_id, "assistant", reply, meta={"source": "cli-chat"})
        click.echo(f"\n{reply}\n")