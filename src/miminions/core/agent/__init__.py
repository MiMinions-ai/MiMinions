"""
Minion Agent Module

This module provides an LLM-powered agent implementation with strong typing, validation, and structured schemas for tools,
inputs, and outputs.

The Agent is designed to:
- Support flexible tool registration from Python functions
- Support memory integration (SQLite)
- Execute tools via LLM reasoning using the async run() API

Example:
    from miminions.core.agent import create_minion

    # Create agent (uses OpenRouter by default; set OPENROUTER_API_KEY in env)
    agent = create_minion(name="MyAgent", description="My helpful agent")

    def add(a: int, b: int) -> int:
        return a + b

    agent.register_tool("add", "Add two numbers", add)

"""

from __future__ import annotations

from .models import (
    AgentConfig,
    AgentState,
)

__all__ = [
    # MiMinions Agent
    "Minion",
    "create_minion",
    "AgentConfig",
    "AgentState",
]


def __getattr__(name: str):
    """Lazily expose heavier agent/runtime imports.

    This keeps lightweight imports such as ContextBuilder usable in tests
    without forcing the full agent stack to load at package import time.
    """
    if name in {"Minion", "create_minion"}:
        from .agent import Minion, create_minion

        if name == "Minion":
            return Minion
        return create_minion

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")