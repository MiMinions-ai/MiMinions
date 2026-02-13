"""
Minion Agent Module

This module provides an agent implementation using pydantic_ai with strong typing,
validation, and structured schemas for tools, inputs, and outputs.

The Agent is designed to:
- Use pydantic_ai for LLM-ready agent infrastructure
- Use Pydantic models for all inputs, outputs, and tool schemas
- Support flexible tool registration from Python functions
- Support memory integration (FAISS, SQLite)
- Execute tools directly or via LLM when model is configured

By default, the agent uses TestModel (no LLM required). Pass a real model
like 'openai:gpt-4' to enable LLM-driven tool execution.

Example:
    from miminions.agent import create_minion, ExecutionStatus
    
    # Create agent (uses TestModel by default, no LLM required)
    agent = create_minion(name="MyAgent")
    
    def add(a: int, b: int) -> int:
        return a + b
    
    agent.register_tool("add", "Add two numbers", add)
    
    # Direct execution (no LLM)
    result = agent.execute("add", a=1, b=2)
    print(result.status)  # ExecutionStatus.SUCCESS
    
    # For LLM execution, set a model:
    # agent.set_model('openai:gpt-4')
    # llm_agent = agent.get_pydantic_ai_agent()
    # result = llm_agent.run_sync("Add 1 and 2")
"""

from .agent import Minion, create_minion
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

from pydantic_ai import Agent as PydanticAIAgent, Tool, RunContext
from pydantic_ai.models.test import TestModel

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
    "TestModel",
]
