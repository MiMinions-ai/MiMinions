"""
Pydantic Agent Module

This module provides a Pydantic-based agent implementation with strong typing,
validation, and structured schemas for tools, inputs, and outputs.

The Pydantic Agent is designed to:
- Use Pydantic models for all inputs, outputs, and tool schemas
- Support tool registration mirroring Simple Agent behavior
- Support memory integration in the same way as Simple Agent
- Execute tools deterministically (explicit calls, no reasoning loop)
- Be structured for easy future LLM integration

Example:
    from miminions.agent.pydantic_agent import PydanticAgent, ToolDefinition
    
    agent = PydanticAgent(name="MyAgent")
    
    def add(a: int, b: int) -> int:
        return a + b
    
    agent.register_tool("add", "Add two numbers", add)
    result = agent.execute("add", {"a": 1, "b": 2})
"""

from .agent import PydanticAgent, create_pydantic_agent
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
    "PydanticAgent",
    "create_pydantic_agent",
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
]
