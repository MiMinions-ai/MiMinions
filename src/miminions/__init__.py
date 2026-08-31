"""
MiMinions - A Python package for managing and interacting with AI assistants

This package provides a generic tool system that can work with multiple AI frameworks
including LangChain, AutoGen, and AGNO.
"""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from pathlib import Path
import tomllib


def _load_local_project_version() -> str | None:
    """Read the source-tree version when running from a checkout."""
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    if not pyproject_path.exists():
        return None
    project = tomllib.loads(pyproject_path.read_text(encoding="utf-8")).get("project", {})
    local_version = project.get("version")
    if isinstance(local_version, str) and local_version.strip():
        return local_version
    return None

try:
    __version__ = _load_local_project_version() or version("miminions")
except PackageNotFoundError:
    __version__ = "0.0.0"  # fallback for uninstalled/editable without metadata

try:
    from .tools import GenericTool, tool, create_tool
    from .agent import Agent
    from .data import LocalDataManager
    from .user import User, UserController

    __all__ = ["__version__", "GenericTool", "tool", "create_tool", "Agent", "LocalDataManager", "User", "UserController"]

except ImportError:
    # In case optional dependencies are not installed
    __all__ = []
