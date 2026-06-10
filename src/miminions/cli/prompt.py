"""One-shot prompt CLI for the MiMinions runtime."""

from __future__ import annotations

import asyncio
from typing import Any

import click

from miminions.agent import create_minion
from miminions.context import ContextBuilder
from miminions.core.workspace import WorkspaceManager, ensure_workspace
from miminions.cli.auth import get_config_dir
from miminions.session.store import JsonlSessionStore


@click.group()
def prompt_cli() -> None:
    """Prompt commands."""
    pass


@prompt_cli.command("ask")
@click.option("--workspace", "workspace_ref", default="default", show_default=True, help="Workspace id or name.")
@click.option("--session", "session_id", default=None, help="Optional existing session id.")
@click.argument("prompt_parts", nargs=-1, required=True)
def ask_prompt(workspace_ref: str, session_id: str | None, prompt_parts: tuple[str, ...]) -> None:
    """Send a single prompt to the Minion runtime."""
    user_prompt = " ".join(prompt_parts).strip()
    if not user_prompt:
        raise click.ClickException("Prompt cannot be empty.")

    asyncio.run(_ask_prompt(workspace_ref, session_id, user_prompt))


async def _ask_prompt(workspace_ref: str, session_id: str | None, user_prompt: str) -> None:
    """Run the one-shot prompt flow and print the assistant response."""
    manager = WorkspaceManager(get_config_dir())
    workspace, root = ensure_workspace(manager, workspace_ref, create_missing=True, init_files=True)

    store = JsonlSessionStore(root)
    if not session_id:
        session_id = store.create_session_id()

    meta: dict[str, Any] = {
        "source": "cli-prompt",
        "workspace_id": workspace.id,
    }

    store.append(session_id, "user", user_prompt, meta=meta)

    context = ContextBuilder().build(workspace, root)
    minion = create_minion(name="MiMinions", description=context)

    try:
        reply = await minion.run(user_prompt)
    except Exception as exc:
        error_text = f"[error] {type(exc).__name__}: {exc}"
        store.append(session_id, "assistant", error_text, meta={**meta, "error": True})
        raise click.ClickException(error_text) from exc

    store.append(session_id, "assistant", reply, meta=meta)
    click.echo(reply)
