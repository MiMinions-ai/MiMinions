"""
AutoGen Tool Adapter

Provides conversion between GenericTool and AutoGen tools.
"""

from typing import Any, Dict, Optional, Union
from autogen_core.tools import FunctionTool
from autogen_core import CancellationToken
from . import GenericTool
import asyncio


class AutoGenToolAdapter:
    """Adapter to convert GenericTool to AutoGen FunctionTool"""
    
    def __init__(self, generic_tool: GenericTool):
        self.generic_tool = generic_tool
        self.autogen_tool = FunctionTool(
            func=generic_tool.func,
            description=generic_tool.description,
            name=generic_tool.name
        )
    
    @property
    def name(self) -> str:
        return self.autogen_tool.name
    
    @property
    def description(self) -> str:
        return self.autogen_tool.description
    
    @property
    def schema(self) -> Dict[str, Any]:
        return self.autogen_tool.schema
    
    async def run(self, args: Dict[str, Any], cancellation_token: Optional[CancellationToken] = None) -> Any:
        """Execute the tool with AutoGen interface"""
        if cancellation_token is None:
            cancellation_token = CancellationToken()
        return await self.autogen_tool.run_json(args, cancellation_token)
    
    def run_sync(self, args: Dict[str, Any]) -> Any:
        """Synchronous execution wrapper"""
        return asyncio.run(self.run(args))


def to_autogen_tool(generic_tool: GenericTool) -> AutoGenToolAdapter:
    """Convert a GenericTool to an AutoGen tool"""
    return AutoGenToolAdapter(generic_tool)


def from_autogen_tool(autogen_tool: FunctionTool) -> GenericTool:
    """Convert an AutoGen tool to a GenericTool"""
    from . import SimpleTool
    
    def wrapper(**kwargs):
        # For conversion, we need to handle the async nature
        # This is a simplified version - in practice you might want
        # to preserve the async nature
        adapter = AutoGenToolAdapter.__new__(AutoGenToolAdapter)
        adapter.autogen_tool = autogen_tool
        return adapter.run_sync(kwargs)
    
    return SimpleTool(
        name=autogen_tool.name,
        description=autogen_tool.description,
        func=wrapper
    )