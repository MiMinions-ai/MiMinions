"""
MCP Tool Adapter

Provides conversion between MCP tools and GenericTool format.
"""

from typing import Any, Dict, Optional, List
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
import asyncio
import json

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent))
from tools import GenericTool, SimpleTool

class MCPToolAdapter:
    """Adapter to work with MCP servers and convert their tools to GenericTool format"""
    
    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.stdio_contexts: Dict[str, Any] = {}
        self.session_contexts: Dict[str, Any] = {}
    
    async def connect_to_server(self, server_name: str, server_params: StdioServerParameters) -> None:
        """Connect to an MCP server"""
        stdio_ctx = stdio_client(server_params)
        read, write = await stdio_ctx.__aenter__()
        self.stdio_contexts[server_name] = stdio_ctx
        
        session = ClientSession(read, write)
        session_ctx = await session.__aenter__()
        await session.initialize()
        
        self.sessions[server_name] = session
        self.session_contexts[server_name] = session_ctx
    
    async def get_tools_from_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get all tools from a specific MCP server"""
        if server_name not in self.sessions:
            raise ValueError(f"Server '{server_name}' not connected")
        
        session = self.sessions[server_name]
        tools_response = await session.list_tools()
        return tools_response.tools if tools_response else []
    
    async def convert_mcp_tool_to_generic(self, mcp_tool: Any, server_name: str) -> GenericTool:
        """Convert an MCP tool to GenericTool format"""
        # Handle both dict and Tool object formats
        if hasattr(mcp_tool, 'name'):
            tool_name = mcp_tool.name
            tool_description = mcp_tool.description if hasattr(mcp_tool, 'description') else ""
        else:
            tool_name = mcp_tool.get("name", "unknown")
            tool_description = mcp_tool.get("description", "")
        
        async def mcp_tool_wrapper(**kwargs):
            if server_name not in self.sessions:
                raise ValueError(f"Server '{server_name}' not connected")
            
            session = self.sessions[server_name]
            result = await session.call_tool(tool_name, kwargs)
            
            # Extract the actual content from the result
            if result and hasattr(result, 'content'):
                content_list = result.content
                if content_list and len(content_list) > 0:
                    # Get the first content item's text
                    first_item = content_list[0]
                    if hasattr(first_item, 'text'):
                        return first_item.text
                    return first_item
                return content_list
            return result
        
        # Return the async function directly as a SimpleTool
        # The SimpleTool will handle it properly
        return SimpleTool(
            name=tool_name,
            description=tool_description,
            func=mcp_tool_wrapper
        )
    
    async def load_all_tools_from_server(self, server_name: str) -> List[GenericTool]:
        """Load all tools from a server and convert them to GenericTool format"""
        mcp_tools = await self.get_tools_from_server(server_name)
        generic_tools = []
        
        for mcp_tool in mcp_tools:
            generic_tool = await self.convert_mcp_tool_to_generic(mcp_tool, server_name)
            generic_tools.append(generic_tool)
        
        return generic_tools
    
    async def close_all_connections(self):
        """Close all server connections"""
        for server_name in list(self.sessions.keys()):
            session = self.sessions[server_name]
            stdio_ctx = self.stdio_contexts.get(server_name)
            
            try:
                await session.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing session for {server_name}: {e}")
            
            try:
                if stdio_ctx:
                    await stdio_ctx.__aexit__(None, None, None)
            except Exception as e:
                print(f"Error closing stdio context for {server_name}: {e}")
        
        self.sessions.clear()
        self.stdio_contexts.clear()
        self.session_contexts.clear()


class MCPTool(GenericTool):
    """GenericTool implementation specifically for MCP tools"""
    
    def __init__(self, name: str, description: str, mcp_schema: Dict[str, Any], call_func: callable):
        self.mcp_schema = mcp_schema
        self.call_func = call_func
        super().__init__(name, description, call_func)
    
    def run(self, **kwargs) -> Any:
        """Execute the MCP tool"""
        return self.call_func(**kwargs)
    
    @classmethod
    def from_mcp_tool(cls, mcp_tool: Dict[str, Any], call_func: callable) -> 'MCPTool':
        """Create an MCPTool from MCP tool definition"""
        return cls(
            name=mcp_tool.get("name", "unknown"),
            description=mcp_tool.get("description", ""),
            mcp_schema=mcp_tool,
            call_func=call_func
        )