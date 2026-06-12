"""
First-run bootstrap for MiMinions.

Creates a default workspace (with prompt, skill, and memory templates),
seeds a default agent, and records both in config.json so commands can
fall back to them when no explicit target is given.
"""

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict

from miminions.core.workspace import WorkspaceManager, resolve_workspace
from miminions.workspace_fs import init_workspace

DEFAULT_WORKSPACE_NAME = "default"
DEFAULT_AGENT_ID = "default"


def _load_json(path: Path) -> Dict[str, Any]:
    """Load a JSON file, returning {} if missing and failing clearly if corrupt."""
    if not path.exists():
        return {}
    try:
        with open(path, "r") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def _save_json(path: Path, data: Dict[str, Any]) -> None:
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def _ensure_default_workspace(config_dir: Path) -> str:
    """Create and initialize the default workspace if needed; return its id."""
    manager = WorkspaceManager(config_dir)
    workspaces = manager.load_workspaces()

    workspace = resolve_workspace(workspaces, DEFAULT_WORKSPACE_NAME)
    if workspace is None:
        workspace = manager.create_workspace(
            DEFAULT_WORKSPACE_NAME,
            description="Default workspace created on first run.",
        )
        workspaces[workspace.id] = workspace

    if not workspace.root_path:
        root = (config_dir / "workspaces" / f"ws_{workspace.id}").resolve()
        workspace.root_path = str(root)

    init_workspace(workspace.root_path)
    manager.save_workspaces(workspaces)
    return workspace.id


def _ensure_default_agent(config_dir: Path) -> str:
    """Seed a default agent record if no agents exist; return the default agent id."""
    agents_file = config_dir / "agents.json"
    agents = _load_json(agents_file)
    if agents:
        return next(iter(agents))

    agents[DEFAULT_AGENT_ID] = {
        "name": "default",
        "description": "Default MiMinions agent created on first run.",
        "type": "assistant",
        "base_agent": "miminions.agent.Minion",
        "mode": "cli_extension",
        "status": "inactive",
        "goal": None,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    _save_json(agents_file, agents)
    return DEFAULT_AGENT_ID


def ensure_default_setup(config_dir: Path) -> Dict[str, Any]:
    """
    Ensure a new user has a working default setup.

    On first run this creates the default workspace (prompt, skills, memory,
    sessions, and data templates included), seeds a default agent, and records
    both in config.json. Later runs cost a single config read.
    """
    config_dir = Path(config_dir)
    config_file = config_dir / "config.json"
    config = _load_json(config_file)

    if config.get("default_workspace"):
        return config

    config_dir.mkdir(parents=True, exist_ok=True)
    config["default_workspace"] = _ensure_default_workspace(config_dir)
    config["default_agent"] = _ensure_default_agent(config_dir)
    _save_json(config_file, config)
    return config
