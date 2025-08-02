"""
Unified Tool Adapter Factory

This module provides a centralized factory for converting GenericTools to different
framework formats, reducing code duplication across adapters.
"""

from typing import Any, Dict, List, Optional, Union, Callable
from . import GenericTool


class AdapterFactory:
    """Factory for creating tool adapters for different frameworks"""
    
    @staticmethod
    def to_langchain(generic_tool: GenericTool) -> Any:
        """Convert GenericTool to LangChain format"""
        try:
            from .langchain_adapter import to_langchain_tool
            return to_langchain_tool(generic_tool)
        except ImportError:
            raise ImportError("LangChain is not installed. Install with: pip install langchain-core")
    
    @staticmethod
    def to_autogen(generic_tool: GenericTool) -> Any:
        """Convert GenericTool to AutoGen format"""
        try:
            from .autogen_adapter import to_autogen_tool
            return to_autogen_tool(generic_tool)
        except ImportError:
            raise ImportError("AutoGen is not installed. Install with: pip install autogen-core")
    
    @staticmethod
    def to_agno(generic_tool: GenericTool) -> Any:
        """Convert GenericTool to AGNO format"""
        try:
            from .agno_adapter import to_agno_tool
            return to_agno_tool(generic_tool)
        except ImportError:
            raise ImportError("AGNO is not installed. Install with: pip install agno")
    
    @staticmethod
    def convert_all(generic_tools: List[GenericTool], framework: str) -> List[Any]:
        """Convert multiple GenericTools to a specific framework format"""
        if framework.lower() == "langchain":
            return [AdapterFactory.to_langchain(tool) for tool in generic_tools]
        elif framework.lower() == "autogen":
            return [AdapterFactory.to_autogen(tool) for tool in generic_tools]
        elif framework.lower() == "agno":
            return [AdapterFactory.to_agno(tool) for tool in generic_tools]
        else:
            raise ValueError(f"Unsupported framework: {framework}. Supported: langchain, autogen, agno")
    
    @staticmethod
    def get_supported_frameworks() -> List[str]:
        """Get list of supported frameworks"""
        frameworks = []
        
        try:
            import langchain_core
            frameworks.append("langchain")
        except ImportError:
            pass
        
        try:
            import autogen_core
            frameworks.append("autogen")
        except ImportError:
            pass
        
        try:
            import agno
            frameworks.append("agno")
        except ImportError:
            pass
        
        return frameworks


# Convenience functions for backward compatibility
def to_langchain_tool(generic_tool: GenericTool) -> Any:
    """Convert GenericTool to LangChain format"""
    return AdapterFactory.to_langchain(generic_tool)


def to_autogen_tool(generic_tool: GenericTool) -> Any:
    """Convert GenericTool to AutoGen format"""
    return AdapterFactory.to_autogen(generic_tool)


def to_agno_tool(generic_tool: GenericTool) -> Any:
    """Convert GenericTool to AGNO format"""
    return AdapterFactory.to_agno(generic_tool) 