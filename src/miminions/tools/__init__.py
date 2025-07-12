"""
Generic Tool Module for MiMinions

This module provides a unified interface for tools that can be used across
different AI frameworks including LangChain, AutoGen, and AGNO.
"""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional, Union, Callable, Type
from dataclasses import dataclass
import inspect
import json


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
        parameters = {}
        required = []
        
        for param_name, param in sig.parameters.items():
            # Get type annotation
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
                schema_type = "string"  # Default fallback
            
            parameters[param_name] = {
                "type": schema_type,
                "description": param_name  # Could be enhanced with docstring parsing
            }
            
            # Check if parameter has default value
            if param.default == inspect.Parameter.empty:
                required.append(param_name)
            else:
                parameters[param_name]["default"] = param.default
        
        return ToolSchema(
            name=self.name,
            description=self.description,
            parameters=parameters,
            required=required
        )
    
    @property
    def schema(self) -> ToolSchema:
        """Get the tool schema"""
        return self._schema
    
    @abstractmethod
    def run(self, **kwargs) -> Any:
        """Execute the tool with given arguments"""
        pass
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert tool to dictionary representation"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {
                "type": "object",
                "properties": self.schema.parameters,
                "required": self.schema.required
            }
        }


class SimpleTool(GenericTool):
    """Simple implementation of GenericTool"""
    
    def run(self, **kwargs) -> Any:
        """Execute the tool function with provided arguments"""
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