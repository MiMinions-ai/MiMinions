"""One-shot prompt CLI for the MiMinions runtime."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click

from miminions.agent import create_minion
from miminions.agent.context_builder import ContextBuilder
from miminions.core.workspace import Workspace, WorkspaceManager
from miminions.interface.cli.auth import get_config_dir
from miminions.session.store import JsonlSessionStore
from miminions.workspace_fs import init_workspace


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


def _resolve_workspace(workspaces: dict[str, Workspace], workspace_ref: str) -> Workspace | None:
    """Resolve a workspace by exact id, id prefix, or exact name."""
    if workspace_ref in workspaces:
        return workspaces[workspace_ref]

    for workspace_id, workspace in workspaces.items():
        if workspace_id.startswith(workspace_ref):
            return workspace
        if str(getattr(workspace, "id", "")) == workspace_ref:
            return workspace
        if str(getattr(workspace, "name", "")) == workspace_ref:
            return workspace

    return None


def _default_root_path(workspace_id: str) -> Path:
    """Return the default on-disk root for a workspace."""
    return (Path("~/.miminions/workspaces").expanduser() / f"ws_{workspace_id}").resolve()


def _ensure_workspace(manager: WorkspaceManager, workspace_ref: str) -> tuple[Workspace, Path]:
    """Resolve or create a workspace and ensure its file layout exists."""
    workspaces = manager.load_workspaces()
    workspace = _resolve_workspace(workspaces, workspace_ref)

    if workspace is None:
        workspace = manager.create_workspace(workspace_ref)
        workspaces[workspace.id] = workspace

    root_path = getattr(workspace, "root_path", None)
    if root_path:
        root = Path(root_path).expanduser().resolve()
    else:
        root = _default_root_path(workspace.id)
        workspace.root_path = str(root)

    init_workspace(root)
    manager.save_workspaces(workspaces)
    return workspace, root


async def _ask_prompt(workspace_ref: str, session_id: str | None, user_prompt: str) -> None:
    """Run the one-shot prompt flow and print the assistant response."""
    manager = WorkspaceManager(get_config_dir())
    workspace, root = _ensure_workspace(manager, workspace_ref)

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
