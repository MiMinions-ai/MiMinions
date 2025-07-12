"""
AGNO Tool Adapter

Provides conversion between GenericTool and AGNO tools.
"""

from typing import Any, Dict, Optional
from agno.tools import Function
from . import GenericTool


class AGNOToolAdapter:
    """Adapter to convert GenericTool to AGNO Function"""
    
    def __init__(self, generic_tool: GenericTool):
        self.generic_tool = generic_tool
        self.agno_function = Function.from_callable(generic_tool.func)
        # Override name and description if they differ
        if self.agno_function.name != generic_tool.name:
            self.agno_function.name = generic_tool.name
        if self.agno_function.description != generic_tool.description:
            self.agno_function.description = generic_tool.description
    
    @property
    def name(self) -> str:
        return self.agno_function.name
    
    @property
    def description(self) -> str:
        return self.agno_function.description
    
    @property
    def schema(self) -> Dict[str, Any]:
        return self.agno_function.to_dict()
    
    def run(self, **kwargs) -> Any:
        """Execute the tool"""
        return self.generic_tool.run(**kwargs)
    
    def to_dict(self) -> Dict[str, Any]:
        """Get AGNO-compatible dictionary representation"""
        return self.agno_function.to_dict()


def to_agno_tool(generic_tool: GenericTool) -> AGNOToolAdapter:
    """Convert a GenericTool to an AGNO tool"""
    return AGNOToolAdapter(generic_tool)


def from_agno_function(agno_function: Function) -> GenericTool:
    """Convert an AGNO Function to a GenericTool"""
    from . import SimpleTool
    
    # Extract the original function from the AGNO Function
    # This is a simplified approach - AGNO Functions may have more complex internals
    def wrapper(**kwargs):
        # For this conversion, we'll need to call the function somehow
        # This is a basic implementation
        return agno_function(**kwargs) if callable(agno_function) else None
    
    return SimpleTool(
        name=agno_function.name,
        description=agno_function.description,
        func=wrapper
    )