"""
MiMinions Agent Module

This module provides agent implementations for the MiMinions framework.

Available agents:
- Simple Agent: Lightweight agent with MCP server support and memory integration
- Pydantic Agent: Strongly-typed agent using Pydantic models for validation

Example:
    # Simple Agent (original)
    from miminions.agent import create_simple_agent
    agent = create_simple_agent("MyAgent")
    
    # Pydantic Agent (new)
    from miminions.agent import create_pydantic_agent
    agent = create_pydantic_agent("MyAgent")
"""

# Simple Agent exports (for backward compatibility)
from .simple_agent import Agent, create_simple_agent

# Pydantic Agent exports
from .pydantic_agent import (
    PydanticAgent,
    create_pydantic_agent,
    ToolDefinition,
    ToolParameter,
    ToolSchema,
    ToolExecutionRequest,
    ToolExecutionResult,
    AgentConfig,
    MemoryEntry,
    MemoryQueryResult,
)

__all__ = [
    # Simple Agent
    "Agent",
    "create_simple_agent",
    # Pydantic Agent
    "PydanticAgent",
    "create_pydantic_agent",
    "ToolDefinition",
    "ToolParameter",
    "ToolSchema",
    "ToolExecutionRequest",
    "ToolExecutionResult",
    "AgentConfig",
    "MemoryEntry",
    "MemoryQueryResult",
]
