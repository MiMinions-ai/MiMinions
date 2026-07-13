"""
First-run bootstrap for MiMinions.

Creates a default workspace (with prompt, skill, and memory templates),
seeds a default agent, and records both in config.json so commands can
fall back to them when no explicit target is given.
"""

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from miminions.core.workspace import WorkspaceManager, resolve_workspace
from miminions.utils.json_io import load_json, save_json
from miminions.workspace_fs import init_workspace

DEFAULT_WORKSPACE_NAME = "default"
DEFAULT_AGENT_ID = "default"


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

    # init_workspace never overwrites existing files, so re-running only
    # fills in whatever is missing.
    init_workspace(workspace.root_path)
    manager.save_workspaces(workspaces)
    return workspace.id


def _ensure_default_agent(config_dir: Path) -> str:
    """Seed a default agent record if no agents exist; return the default agent id."""
    agents_file = config_dir / "agents.json"
    agents = load_json(agents_file)
    if agents:
        return DEFAULT_AGENT_ID if DEFAULT_AGENT_ID in agents else next(iter(agents))

    agents[DEFAULT_AGENT_ID] = {
        "name": "default",
        "description": "Default MiMinions agent created on first run.",
        "type": "assistant",
        "base_agent": "miminions.agent.Minion",
        "mode": "cli_extension",
        "status": "inactive",
        "goal": None,
        "created_at": datetime.now(UTC).isoformat(),
    }
    save_json(agents_file, agents)
    return DEFAULT_AGENT_ID


def ensure_default_setup(config_dir: Path, force: bool = False) -> dict[str, Any]:
    """
    Ensure a user has a working default setup.

    On first run this creates the default workspace (prompt, skills, memory,
    sessions, and data templates included), seeds a default agent, and records
    both in config.json. Later runs cost a single config read.

    If force=True, bootstrap/repair logic is re-run even when defaults already
    exist so missing workspace template files can be restored.
    """
    config_file = config_dir / "config.json"
    config = load_json(config_file)

    if config.get("default_workspace") and not force:
        return config

    config_dir.mkdir(parents=True, exist_ok=True)

    workspace_id = _ensure_default_workspace(config_dir)
    agent_id = _ensure_default_agent(config_dir)

    if not config.get("default_workspace"):
        config["default_workspace"] = workspace_id
    if not config.get("default_agent"):
        config["default_agent"] = agent_id

    save_json(config_file, config)
    return config
