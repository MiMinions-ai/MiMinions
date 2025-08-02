"""
MiMinions - A Python package for managing and interacting with AI assistants

This package provides a generic tool system that can work with multiple AI frameworks
including LangChain, AutoGen, and AGNO.
"""

try:
    from .tools import GenericTool, tool, create_tool
    from .agent import Agent
    from .agents import BaseAgent

    __version__ = "0.1.0"
    __all__ = ["GenericTool", "tool", "create_tool", "Agent", "BaseAgent"]
except ImportError:
    # In case optional dependencies are not installed
    __all__ = []
