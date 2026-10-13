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

# The former eager import attempted a removed ``agent.Agent`` export and loaded
# the model stack before every CLI acknowledgement. Preserve the available tool
# shortcuts lazily, and the existing empty wildcard-export contract.
__all__ = []


def __getattr__(name: str):
    if name in {"GenericTool", "tool", "create_tool"}:
        from importlib import import_module
        value = getattr(import_module("miminions.tools"), name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
