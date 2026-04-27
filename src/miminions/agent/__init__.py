"""
Minion Agent Module

This module provides an LLM-powered agent implementation built on top of
pydantic_ai with strong typing, validation, and structured schemas for tools,
inputs, and outputs.

The Agent is designed to:
- Use pydantic_ai for LLM-backed agent infrastructure
- Default to OpenRouter (openai/gpt-oss-20b:free) — set OPENROUTER_API_KEY
- Use Pydantic models for all inputs, outputs, and tool schemas
- Support flexible tool registration from Python functions
- Support memory integration (SQLite)
- Execute tools via LLM reasoning using the async run() API

Example:
    from miminions.agent import create_minion

    # Create agent (uses OpenRouter by default; set OPENROUTER_API_KEY in env)
    agent = create_minion(name="MyAgent", description="My helpful agent")

    def add(a: int, b: int) -> int:
        return a + b

    agent.register_tool("add", "Add two numbers", add)

    # LLM-powered execution — the model decides when to call tools
    import asyncio
    reply = asyncio.run(agent.run("What is 3 + 7?"))
    print(reply)  # "The answer is 10."

    # To use a different model:
    from pydantic_ai.models.openai import OpenAIModel
    agent = create_minion(name="MyAgent", model=OpenAIModel("gpt-4o"))
"""

from __future__ import annotations

from .context_builder import ContextBuilder
from .models import (
    ToolDefinition,
    ToolParameter,
    ToolSchema,
    ToolExecutionRequest,
    ToolExecutionResult,
    ExecutionStatus,
    ParameterType,
    AgentConfig,
    AgentState,
    MemoryEntry,
    MemoryQueryResult,
)

__all__ = [
    # MiMinions Agent
    "Minion",
    "create_minion",
    # Models
    "ToolDefinition",
    "ToolParameter",
    "ToolSchema",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "ExecutionStatus",
    "ParameterType",
    "AgentConfig",
    "AgentState",
    "MemoryEntry",
    "MemoryQueryResult",
    # pydantic_ai re-exports
    "PydanticAIAgent",
    "Tool",
    "RunContext",
    # Context
    "ContextBuilder",
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

    if name in {"PydanticAIAgent", "Tool", "RunContext"}:
        from pydantic_ai import Agent as PydanticAIAgent, Tool, RunContext

        exports = {
            "PydanticAIAgent": PydanticAIAgent,
            "Tool": Tool,
            "RunContext": RunContext,
        }
        return exports[name]

    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")