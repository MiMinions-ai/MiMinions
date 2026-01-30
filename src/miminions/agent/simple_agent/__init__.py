"""
Simple Agent Module

This module provides a simple agent implementation that can dynamically load tools 
from MCP servers and use them alongside regular generic tools, with integrated 
memory capabilities.

Example:
    from miminions.agent.simple_agent import Agent, create_simple_agent
    
    agent = create_simple_agent("MyAgent", "Description of my agent")
    
    def add(a: int, b: int) -> int:
        return a + b
    
    agent.add_function_as_tool("add", "Add two numbers", add)
    result = agent.execute_tool("add", a=1, b=2)
"""

from .agent import Agent, create_simple_agent

__all__ = [
    "Agent",
    "create_simple_agent",
]
