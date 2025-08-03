"""
Simple Agent Module

Provides a simple agent that can work with generic tools and different frameworks.
"""

from typing import List, Dict, Any, Optional, Union
from ..tools import GenericTool
from ..tools.langchain_adapter import to_langchain_tool
from ..tools.autogen_adapter import to_autogen_tool
from ..tools.agno_adapter import to_agno_tool


class Agent:
    """Simple agent that can work with generic tools"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tools: List[GenericTool] = []
    
    def add_tool(self, tool: GenericTool) -> None:
        """Add a generic tool to the agent"""
        self.tools.append(tool)
    
    def get_tool(self, name: str) -> Optional[GenericTool]:
        """Get a tool by name"""
        for tool in self.tools:
            if tool.name == name:
                return tool
        return None
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return [tool.name for tool in self.tools]
    
    def get_tools_schema(self) -> List[Dict[str, Any]]:
        """Get schema for all tools"""
        return [tool.to_dict() for tool in self.tools]
    
    def execute_tool(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name"""
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found")
        return tool.run(**kwargs)
    
    def to_langchain_tools(self) -> List[Any]:
        """Convert all tools to LangChain format"""
        return [to_langchain_tool(tool) for tool in self.tools]
    
    def to_autogen_tools(self) -> List[Any]:
        """Convert all tools to AutoGen format"""
        return [to_autogen_tool(tool) for tool in self.tools]
    
    def to_agno_tools(self) -> List[Any]:
        """Convert all tools to AGNO format"""
        return [to_agno_tool(tool) for tool in self.tools]
    
    def __str__(self) -> str:
        return f"Agent({self.name}, tools={len(self.tools)})"
    
    def __repr__(self) -> str:
        return self.__str__() 