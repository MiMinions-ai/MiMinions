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
    
    async def connect_to_server(self, server_name: str, server_params: StdioServerParameters) -> None:
        """Connect to an MCP server"""
        async with stdio_client(server_params) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                self.sessions[server_name] = session
    
    async def get_tools_from_server(self, server_name: str) -> List[Dict[str, Any]]:
        """Get all tools from a specific MCP server"""
        if server_name not in self.sessions:
            raise ValueError(f"Server '{server_name}' not connected")
        
        session = self.sessions[server_name]
        tools_response = await session.list_tools()
        return tools_response.tools if tools_response else []
    
    async def convert_mcp_tool_to_generic(self, mcp_tool: Dict[str, Any], server_name: str) -> GenericTool:
        """Convert an MCP tool to GenericTool format"""
        tool_name = mcp_tool.get("name", "unknown")
        tool_description = mcp_tool.get("description", "")
        
        async def mcp_tool_wrapper(**kwargs):
            if server_name not in self.sessions:
                raise ValueError(f"Server '{server_name}' not connected")
            
            session = self.sessions[server_name]
            result = await session.call_tool(tool_name, kwargs)
            return result.content if result else None
        
        # Create a sync wrapper for the async function
        def sync_wrapper(**kwargs):
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    import concurrent.futures
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(asyncio.run, mcp_tool_wrapper(**kwargs))
                        return future.result()
                else:
                    return loop.run_until_complete(mcp_tool_wrapper(**kwargs))
            except RuntimeError:
                # No event loop running, create one
                return asyncio.run(mcp_tool_wrapper(**kwargs))
        
        return SimpleTool(
            name=tool_name,
            description=tool_description,
            func=sync_wrapper
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
        for session in self.sessions.values():
            if hasattr(session, 'close'):
                await session.close()
        self.sessions.clear()


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