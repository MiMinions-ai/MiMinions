"""
MiMinions - A Python package for managing and interacting with AI assistants

This package provides a generic tool system that can work with multiple AI frameworks
including LangChain, AutoGen, and AGNO.
"""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("miminions")
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
