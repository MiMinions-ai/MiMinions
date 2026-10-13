"""Interactive async chat CLI — user messages go to the Minion, replies come back."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import click

from miminions.core.paths import get_config_dir
from miminions.cli.config import load_config
from miminions.session.store import JsonlSessionStore
from miminions.core.workspace import WorkspaceManager, ensure_workspace


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
    from miminions.memory import MemoryDistiller
    if model is not None:
        from miminions.memory import create_llm_filter

        llm_filter = create_llm_filter(model)
    else:
        # Fallback: workspace-provided filter or empty placeholder.
        if hasattr(workspace, "memory_llm_filter"):
            llm_filter = getattr(workspace, "memory_llm_filter")
        else:
            llm_filter = lambda **_kw: {"history_summary": "", "workspace_facts": [], "global_insights": []}

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
    default=None,
    help="Workspace id or name. Defaults to the configured default workspace.",
)
@click.option(
    "--session",
    "session_id",
    default=None,
    help="Resume an existing session id (loads prior history for LLM context).",
)
@click.option(
    "--verbose",
    is_flag=True,
    default=False,
    help="Show tool calls, token usage and latency per turn.",
)
def chat_command(workspace_ref: str | None, session_id: str | None, verbose: bool) -> None:
    """Start an interactive async chat session for a workspace."""
    if verbose:
        logging.basicConfig(level=logging.INFO)
    if not workspace_ref:
        config = load_config()

        if not isinstance(config, dict):
            raise click.ClickException("Invalid config format; expected a dictionary.")

        default_workspace = config.get("default_workspace")
        if not isinstance(default_workspace, str) or not default_workspace:
            raise click.ClickException(
                "No --workspace given and no default workspace configured."
            )
        
        workspace_ref = default_workspace
    asyncio.run(_chat_loop(workspace_ref, session_id, verbose))


# ---------------------------------------------------------------------------
# Async chat loop
# ---------------------------------------------------------------------------


async def _chat_loop(workspace_ref: str, session_id: str | None, verbose: bool = False) -> None:
    """Interactive terminal frontend; the execution instance owns every turn."""
    from .dispatch import submit_task
    from miminions.execution.models import conversation_key
    manager = WorkspaceManager(get_config_dir())
    try:
        workspace, root = ensure_workspace(manager, workspace_ref)
    except (ValueError, FileNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc
    store = JsonlSessionStore(root)
    session_id = (session_id or store.create_session_id()).strip()
    try:
        store.path_for(session_id)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    session_key = conversation_key(workspace.id, session_id)
    workspace_name = getattr(workspace, "name", getattr(workspace, "id", "unknown"))
    click.echo(f"Workspace : {workspace_name}")
    click.echo(f"Session   : {session_id}")
    click.echo("Type '/exit' or '/quit' to end the session.\n")
    submitted = False
    try:
        while True:
            try:
                user_text = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                click.echo("\nSession ended.")
                break
            if not user_text:
                continue
            if user_text in {"/exit", "/quit"}:
                click.echo("Session ended.")
                break
            submitted = True
            try:
                submit_task("chat_turn", {"workspace": workspace.id, "session_id": session_id,
                                          "prompt": user_text, "verbose": verbose},
                            session_key=session_key, home=get_config_dir())
            except click.exceptions.Exit as exc:
                if exc.exit_code == 130:
                    raise
                # Failed turns remain in the transcript and the user can continue.
            except click.ClickException as exc:
                click.echo(f"Error: {exc}", err=True)
    finally:
        if submitted:
            # A detached in-flight turn precedes finalization through the session queue.
            try:
                click.echo("Queuing session memory distillation...", err=True)
                submit_task("session_distill", {"workspace": workspace.id, "session_id": session_id},
                            detach=True, session_key=session_key, home=get_config_dir())
            except click.ClickException as exc:
                click.echo(f"Warning: session distillation could not be submitted: {exc}", err=True)
