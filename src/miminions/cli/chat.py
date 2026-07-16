"""Interactive async chat CLI — user messages go to the Minion, replies come back."""

from __future__ import annotations

import asyncio
import logging
from pathlib import Path
from typing import Any

import click
from pydantic_ai.usage import RunUsage

from miminions.agent import create_minion
from miminions.memory import MemoryDistiller
from miminions.session.store import JsonlSessionStore
from miminions.core.workspace import WorkspaceManager, ensure_workspace
from miminions.cli.auth import get_config, get_config_dir


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
        from miminions.memory import create_llm_filter

        llm_filter = create_llm_filter(model)
    else:
        # Fallback: workspace-provided filter or empty placeholder.
        llm_filter = getattr(workspace, "memory_llm_filter", None)
        if not callable(llm_filter):
            def llm_filter(**_kw):
                return {"history_summary": "", "workspace_facts": [], "global_insights": []}

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
        workspace_ref = get_config().get("default_workspace")
        if not workspace_ref:
            raise click.ClickException(
                "No --workspace given and no default workspace configured."
            )
    asyncio.run(_chat_loop(workspace_ref, session_id, verbose))


# ---------------------------------------------------------------------------
# Async chat loop
# ---------------------------------------------------------------------------


def _print_tool_call(name: str, args: dict[str, Any]) -> None:
    """Verbose-mode hook: show each tool invocation on stderr."""
    click.secho(f"  [tool] {name} {args}", dim=True, err=True)


def _print_turn_end(usage: RunUsage, latency: float) -> None:
    """Verbose-mode hook: show token usage and latency on stderr."""
    click.secho(
        f"  [turn] {usage.input_tokens or 0} in / {usage.output_tokens or 0} out tokens, "
        f"{usage.tool_calls} tool call(s), {latency:.1f}s",
        dim=True,
        err=True,
    )


async def _chat_loop(workspace_ref: str, session_id: str | None, verbose: bool = False) -> None:
    """Main async chat loop.

    1. Resolve the workspace and build the root path.
    2. Create the Minion once — it lives for the entire session.
    3. Wire workspace context via set_context() so the LLM sees it.
    4. If resuming a session, load prior JSONL as pydantic_ai messages.
    5. Loop: input → minion.run() → print reply.
    6. On exit, run session distillation in the finally block.
    """
    manager = WorkspaceManager(get_config_dir())
    try:
        workspace, root = ensure_workspace(manager, workspace_ref)
    except (ValueError, FileNotFoundError) as exc:
        raise click.ClickException(str(exc)) from exc

    store = JsonlSessionStore(root)

    if not session_id:
        session_id = store.create_session_id()

    # Build the Minion once — it keeps its tools and model for the session.
    workspace_name = getattr(workspace, "name", getattr(workspace, "id", "unknown"))
    minion = create_minion(
        name="MiMinions",
        description=f"MiMinions agent for workspace '{workspace_name}'.",  # TODO: make customizable per workspace
        on_tool_call=_print_tool_call if verbose else None,
        on_turn_end=_print_turn_end if verbose else None,
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
    click.echo("Type '/exit' or '/quit' to end the session.\n")

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
