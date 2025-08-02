"""
Agent Module

Provides a simple agent that can work with generic tools and different frameworks.
"""

from typing import List, Dict, Any, Optional, Union
from .tools import GenericTool
from .tools.adapter_factory import AdapterFactory
from .core.common import ToolManager


class Agent(ToolManager):
    """Simple agent that can work with generic tools"""
    
    def __init__(self, name: str, description: str = ""):
        super().__init__()
        self.name = name
        self.description = description
        self.generic_tools: List[GenericTool] = []
    
    def add_tool(self, tool: GenericTool) -> None:
        """Add a generic tool to the agent"""
        self.generic_tools.append(tool)
        # Also add to the base tool manager for execution
        super().add_tool(tool.name, tool.run)
    
    def get_tool(self, name: str) -> Optional[GenericTool]:
        """Get a tool by name"""
        for tool in self.generic_tools:
            if tool.name == name:
                return tool
        return None
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return [tool.name for tool in self.generic_tools]
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get schema for all tools"""
        return [tool.to_dict() for tool in self.generic_tools]
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name"""
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found")
        return tool.run(**kwargs)
    
    def to_langchain_tools(self) -> List[Any]:
        """Convert all tools to LangChain format"""
        return AdapterFactory.convert_all(self.generic_tools, "langchain")
    
    def to_autogen_tools(self) -> List[Any]:
        """Convert all tools to AutoGen format"""
        return AdapterFactory.convert_all(self.generic_tools, "autogen")
    
    def to_agno_tools(self) -> List[Any]:
        """Convert all tools to AGNO format"""
        return AdapterFactory.convert_all(self.generic_tools, "agno")
    
    def __str__(self) -> str:
        return f"Agent({self.name}, tools={len(self.generic_tools)})"
    
    def __repr__(self) -> str:
        return self.__str__()