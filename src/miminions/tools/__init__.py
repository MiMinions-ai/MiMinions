"""
Generic Tool Module for MiMinions

This module provides a unified interface for tools that can be used across
different AI frameworks including LangChain, AutoGen, and AGNO.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Callable
from dataclasses import dataclass
import inspect

# Export main classes
__all__ = [
    "ToolSchema",
    "GenericTool",
    "SimpleTool",
    "create_tool",
    "tool",
]


@dataclass
class ToolSchema:
    """Schema representation for a tool"""
    name: str
    description: str
    parameters: Dict[str, Any]
    required: list[str]


class GenericTool(ABC):
    """Base class for generic tools that can be adapted to different frameworks"""

    def __init__(self, name: str, description: str, func: Callable):
        self.name = name
        self.description = description
        self.func = func
        self._schema = self._extract_schema()

    def _extract_schema(self) -> ToolSchema:
        """Extract schema from function signature"""
        sig = inspect.signature(self.func)
        parameters: Dict[str, Any] = {}
        required: list[str] = []

        for param_name, param in sig.parameters.items():
            param_type = param.annotation
            if param_type == inspect.Parameter.empty:
                param_type = str  # Default to string if no annotation

            # Convert Python types to JSON schema types
            if param_type == int:
                schema_type = "integer"
            elif param_type == float:
                schema_type = "number"
            elif param_type == bool:
                schema_type = "boolean"
            elif param_type == str:
                schema_type = "string"
            else:
                schema_type = "string"

            parameters[param_name] = {
                "type": schema_type,
                "description": param_name,
            }

            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                parameters[param_name]["default"] = param.default

        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=parameters,
            required=required,
        )

    @property
    def schema(self) -> ToolSchema:
        """Get the tool schema"""
        return self._schema

    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Execute the tool with given arguments (sync)"""
        raise NotImplementedError

    async def arun(self, **kwargs) -> Any:
        """
        Execute the tool asynchronously.

        - If the underlying function is async, it will be awaited.
        - Otherwise it falls back to sync run().
        """
        if inspect.iscoroutinefunction(self.func):
            return await self.func(**kwargs)
        return self.run(**kwargs)

    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.schema.parameters,
                "required": self.schema.required,
            },
        }


class SimpleTool(GenericTool):
    """Simple implementation of GenericTool"""

    def run(self, **kwargs) -> Any:
        """Execute the tool function with provided arguments (sync)"""
        return self.func(**kwargs)


def create_tool(name: str, description: str, func: Callable) -> GenericTool:
    """Factory function to create a generic tool"""
    return SimpleTool(name=name, description=description, func=func)


def tool(name: Optional[str] = None, description: Optional[str] = None):
    """Decorator to create a generic tool from a function"""
    def decorator(func: Callable) -> GenericTool:
        tool_name = name or func.__name__
        tool_description = description or func.__doc__ or f"Tool: {tool_name}"
        return create_tool(tool_name, tool_description, func)
    return decorator
