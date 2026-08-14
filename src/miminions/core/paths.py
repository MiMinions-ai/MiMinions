"""Central filesystem-path resolution for MiMinions.

All persistent state lives under a single base directory (default
``~/.miminions``). The location is overridable via the ``MIMINIONS_HOME``
environment variable so tests and alternate deployments can redirect every
path at once instead of chasing hardcoded ``~/.miminions`` strings spread
across the codebase.
"""

from __future__ import annotations

import os
from pathlib import Path

DEFAULT_DIR_NAME = ".miminions"
HOME_ENV_VAR = "MIMINIONS_HOME"


def get_config_dir(create: bool = True) -> Path:
    """Return the base MiMinions state directory.

    Honors the ``MIMINIONS_HOME`` environment variable; otherwise falls back
    to ``~/.miminions``. The directory is created by default so callers that
    immediately write into it don't have to.
    """
    override = os.environ.get(HOME_ENV_VAR)
    base = Path(override).expanduser() if override else Path.home() / DEFAULT_DIR_NAME
    if create:
        base.mkdir(parents=True, exist_ok=True)
    return base


def get_workspaces_root() -> Path:
    """Return the directory that holds per-workspace folders."""
    return get_config_dir(create=False) / "workspaces"


def get_global_memory_db_path(create_dir: bool = True) -> str:
    """Return the canonical path for the cross-workspace global memory DB."""
    path = get_config_dir(create=False) / "global_memory.db"
    if create_dir:
        path.parent.mkdir(parents=True, exist_ok=True)
    return str(path)
