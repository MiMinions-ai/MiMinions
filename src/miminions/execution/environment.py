"""Provider credentials scoped to one execution task, never to its supervisor."""

from __future__ import annotations

import os
from contextlib import contextmanager
from pathlib import Path

from dotenv import dotenv_values

PROVIDER_KEYS = (
    "OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY", "GOOGLE_API_KEY",
)


def provider_env_path(context) -> Path:
    """Use the selected project's file, otherwise only the captured task directory."""
    from miminions.core.workspace import WorkspaceManager, resolve_workspace

    workspace_ref = context.params.get("workspace")
    if isinstance(workspace_ref, str):
        workspaces = WorkspaceManager(context.store.home).load_workspaces()
        workspace = resolve_workspace(workspaces, workspace_ref)
        if workspace and workspace.state.get("project_root"):
            return Path(workspace.state["project_root"]).expanduser().resolve() / ".env"
    return Path(context.task.request.cwd or Path.cwd()).expanduser().resolve() / ".env"


@contextmanager
def provider_environment(context):
    """Fill missing API variables and restore them when this task finishes.

    Production tasks each have their own process. Restoration also keeps inline
    integrations and repeated handler calls from retaining another project's key.
    """
    path = provider_env_path(context)
    try:
        with path.open(encoding="utf-8-sig") as stream:
            values = dotenv_values(stream=stream)
    except FileNotFoundError:
        values = {}
    except (OSError, UnicodeError):
        # Exception messages from file parsers must never echo credential contents.
        raise ValueError(f"Cannot read provider API credentials from {path}. Check file access and UTF-8 encoding.") from None

    previous = {}
    try:
        for name in PROVIDER_KEYS:
            value = values.get(name)
            if not os.environ.get(name) and value and value.strip():
                previous[name] = os.environ.get(name)
                os.environ[name] = value.strip()
        try:
            yield path
        except ValueError as exc:
            if str(exc).startswith("OPENROUTER_API_KEY is not set"):
                raise ValueError(f"{exc} CLI credential file: {path}") from None
            raise
    finally:
        for name, value in previous.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
