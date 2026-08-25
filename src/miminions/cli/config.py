"""
General configuration commands for MiMinions CLI.
"""

from __future__ import annotations
from typing import Any
from pathlib import Path

import click

from miminions.core.paths import get_config_dir
from miminions.core.workspace import WorkspaceManager, resolve_workspace
from miminions.utils.json_io import load_json, save_json

_ALLOWED_KEYS = ("default_workspace", "default_agent")


def get_config_file() -> Path:
    return get_config_dir() / "config.json"


def load_config() -> dict[str, object]:
    try:
        config: dict[str, Any] = load_json(get_config_file())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if not isinstance(config, dict):
        raise click.ClickException("Invalid config.json: expected a JSON object")
    return config


def _validate_key(key: str) -> None:
    if key not in _ALLOWED_KEYS:
        allowed = ", ".join(_ALLOWED_KEYS)
        raise click.ClickException(f"Unsupported key '{key}'. Supported keys: {allowed}")


def _resolve_workspace_id(config_dir: Path, workspace_ref: str) -> str:
    manager = WorkspaceManager(config_dir)
    workspaces = manager.load_workspaces()
    workspace = resolve_workspace(workspaces, workspace_ref)
    if workspace is None:
        raise click.ClickException(f"Workspace not found: {workspace_ref}")
    return workspace.id


def _resolve_agent_id(config_dir: Path, agent_id: str) -> str:
    try:
        agents = load_json(config_dir / "agents.json")
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    if not isinstance(agents, dict):
        raise click.ClickException("Invalid agents.json: expected a JSON object")

    if agent_id not in agents:
        raise click.ClickException(f"Agent not found: {agent_id}")
    return agent_id


def _normalized_value(key: str, value: str) -> str:
    config_dir = get_config_dir()
    if key == "default_workspace":
        return _resolve_workspace_id(config_dir, value)
    if key == "default_agent":
        return _resolve_agent_id(config_dir, value)
    raise click.ClickException(f"Unsupported key '{key}'")


@click.group("config")
def config_cli() -> None:
    """Get or set top-level CLI configuration values."""


@config_cli.command("get")
@click.argument("key")
def config_get(key: str) -> None:
    """Get one config value by key."""
    _validate_key(key)
    config = load_config()
    value = config.get(key)
    if value is None:
        raise click.ClickException(f"Key '{key}' is not set")
    click.echo(str(value))


@config_cli.command("set")
@click.argument("key")
@click.argument("value")
def config_set(key: str, value: str) -> None:
    """Set one config value by key."""
    _validate_key(key)
    config = load_config()
    config[key] = _normalized_value(key, value)
    save_json(get_config_file(), config, ensure_parent=True)
    click.echo(f"{key} set to {config[key]}")
