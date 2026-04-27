"""Interactive async chat CLI — user messages go to the Minion, replies come back."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

import click

from miminions.agent import create_minion
from miminions.memory import MemoryDistiller
from miminions.session.store import JsonlSessionStore
from miminions.core.workspace import WorkspaceManager
from miminions.interface.cli.auth import get_config_dir


# ---------------------------------------------------------------------------
# Workspace resolution
# ---------------------------------------------------------------------------


def _resolve_workspace(manager: Any, workspace_ref: str) -> Any:
    """Resolve a workspace by id or name using WorkspaceManager.load_workspaces()."""
    workspaces = manager.load_workspaces()

    if not workspaces:
        return None

    # Try exact dict key match
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


# ---------------------------------------------------------------------------
# Post-session distillation
# ---------------------------------------------------------------------------


def _run_session_distillation(
    workspace: Any,
    root: Path,
    session_id: str,
    model: Any = None,
) -> None:
    """Run post-session memory distillation.

    If *model* is provided the distiller uses the real LLM to extract
    memory from the transcript.  Otherwise it falls back to a placeholder
    filter that produces empty results (the pipeline still runs, just
    without extraction).
    """
    if model is not None:
        from miminions.memory.distiller import create_llm_filter

        llm_filter = create_llm_filter(model)
    else:
        # Fallback: workspace-provided filter or empty placeholder.
        llm_filter = getattr(workspace, "memory_llm_filter", None)
        if not callable(llm_filter):
            llm_filter = lambda **_kw: {
                "history_summary": "",
                "workspace_facts": [],
                "global_insights": [],
            }

    MemoryDistiller(llm_filter=llm_filter).distill_session(
        workspace=workspace,
        root_path=str(root),
        session_id=session_id,
    )


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


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
    help="Resume an existing session id (loads prior history for LLM context).",
)
def chat_command(workspace_ref: str, session_id: str | None) -> None:
    """Start an interactive async chat session for a workspace."""
    asyncio.run(_chat_loop(workspace_ref, session_id))


# ---------------------------------------------------------------------------
# Async chat loop
# ---------------------------------------------------------------------------


async def _chat_loop(workspace_ref: str, session_id: str | None) -> None:
    """Main async chat loop.

    1. Resolve the workspace and build the root path.
    2. Create the Minion once — it lives for the entire session.
    3. Wire workspace context via set_context() so the LLM sees it.
    4. If resuming a session, load prior JSONL as pydantic_ai messages.
    5. Loop: input → minion.run() → print reply.
    6. On exit, run session distillation in the finally block.
    """
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

    store = JsonlSessionStore(root)

    if not session_id:
        session_id = store.create_session_id()

    # Build the Minion once — it keeps its tools and model for the session.
    workspace_name = getattr(workspace, "name", getattr(workspace, "id", "unknown"))
    minion = create_minion(
        name="MiMinions",
        description=f"MiMinions agent for workspace '{workspace_name}'.",
    )
    minion.set_context(workspace, root)

    # If resuming a session, seed message_history from the prior JSONL so
    # the LLM has context from the previous conversation.
    if hasattr(store, "load_as_pydantic_messages"):
        message_history = store.load_as_pydantic_messages(session_id)
    else:
        message_history = []

    click.echo(f"Workspace : {workspace_name}")
    click.echo(f"Session   : {session_id}")
    click.echo("Model     : openai/gpt-oss-20b:free via OpenRouter")
    click.echo("Type 'exit' or 'quit' to end the session.\n")

    try:
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

            store.append(
                session_id,
                "user",
                user_text,
                meta={"source": "cli-chat"},
            )

            try:
                reply = await minion.run(
                    user_text,
                    message_history=message_history,
                )
                # Update history so the LLM remembers prior turns.
                message_history = minion._last_messages
            except Exception as exc:
                reply = f"[error] {type(exc).__name__}: {exc}"

            store.append(
                session_id,
                "assistant",
                reply,
                meta={"source": "cli-chat"},
            )

            click.echo(f"\n{reply}\n")
    finally:
        try:
            _run_session_distillation(
                workspace=workspace,
                root=root,
                session_id=session_id,
                model=minion._model,
            )
        except Exception as exc:
            click.echo(f"Warning: memory distillation skipped: {exc}", err=True)