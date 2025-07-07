"""
LangChain Tool Adapter

Provides conversion between GenericTool and LangChain tools.
"""

from typing import Any, Dict, Optional, Type
from langchain_core.tools import BaseTool
from . import GenericTool


class LangChainToolAdapter(BaseTool):
    """Adapter to convert GenericTool to LangChain BaseTool"""
    
    generic_tool: GenericTool
    
    def __init__(self, generic_tool: GenericTool, **kwargs):
        super().__init__(
            generic_tool=generic_tool,
            name=generic_tool.name,
            description=generic_tool.description,
            **kwargs
        )
    
    def _run(self, **kwargs) -> Any:
        """Execute the generic tool"""
        return self.generic_tool.run(**kwargs)
    
    async def _arun(self, **kwargs) -> Any:
        """Async execution (delegates to sync version)"""
        return self._run(**kwargs)


def to_langchain_tool(generic_tool: GenericTool) -> LangChainToolAdapter:
    """Convert a GenericTool to a LangChain tool"""
    return LangChainToolAdapter(generic_tool)


def from_langchain_tool(langchain_tool: BaseTool) -> GenericTool:
    """Convert a LangChain tool to a GenericTool"""
    from . import SimpleTool
    
    def wrapper(**kwargs):
        return langchain_tool._run(**kwargs)
    
    return SimpleTool(
        name=langchain_tool.name,
        description=langchain_tool.description,
        func=wrapper
    )