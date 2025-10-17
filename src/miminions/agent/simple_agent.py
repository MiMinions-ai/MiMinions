"""
Enhanced Simple Agent with MCP Server Support

This module provides an enhanced agent that can dynamically load tools from MCP servers
and use them alongside regular generic tools.
"""

import asyncio
from typing import List, Dict, Any, Optional, Union
from mcp import StdioServerParameters

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent))
from tools import GenericTool, SimpleTool
from tools.mcp_adapter import MCPToolAdapter

class Agent:
    """Enhanced simple agent that can work with MCP servers and generic tools"""
    
    def __init__(self, name: str, description: str = ""):
        self.name = name
        self.description = description
        self.tools: List[GenericTool] = []
        self.mcp_adapter = MCPToolAdapter()
        self.connected_servers: Dict[str, StdioServerParameters] = {}
    
    async def connect_mcp_server(self, server_name: str, server_params: StdioServerParameters):
        """Connect to an MCP server"""
        await self.mcp_adapter.connect_to_server(server_name, server_params)
        self.connected_servers[server_name] = server_params
        print(f"Connected to MCP server: {server_name}")
    
    async def load_tools_from_mcp_server(self, server_name: str):
        """Load all tools from a specific MCP server"""
        if server_name not in self.connected_servers:
            raise ValueError(f"Server '{server_name}' not connected. Connect first using connect_mcp_server()")
        
        tools = await self.mcp_adapter.load_all_tools_from_server(server_name)
        for tool in tools:
            self.add_tool(tool)
        
        print(f"Loaded {len(tools)} tools from MCP server: {server_name}")
        return tools
    
    async def load_tools_from_all_servers(self):
        """Load tools from all connected MCP servers"""
        all_tools = []
        for server_name in self.connected_servers.keys():
            tools = await self.load_tools_from_mcp_server(server_name)
            all_tools.extend(tools)
        return all_tools
    
    def add_tool(self, tool: GenericTool) -> None:
        """Add a generic tool to the agent"""
        existing = self.get_tool(tool.name)
        if existing:
            print(f"Warning: Tool '{tool.name}' already exists, replacing...")
            self.tools = [t for t in self.tools if t.name != tool.name]
        
        self.tools.append(tool)
    
    def add_function_as_tool(self, name: str, description: str, func: callable) -> None:
        """Add a regular Python function as a tool"""
        tool = SimpleTool(name=name, description=description, func=func)
        self.add_tool(tool)
    
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
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {self.list_tools()}")
        
        try:
            result = tool.run(**kwargs)
            return result
        except Exception as e:
            raise RuntimeError(f"Error executing tool '{tool_name}': {str(e)}")
    
    async def execute_tool_async(self, tool_name: str, **kwargs) -> Any:
        """Execute a tool by name (async version for MCP tools)"""
        return self.execute_tool(tool_name, **kwargs)
    
    def get_tool_info(self, tool_name: str) -> Optional[Dict[str, Any]]:
        """Get detailed information about a specific tool"""
        tool = self.get_tool(tool_name)
        if tool is None:
            return None
        
        return {
            "name": tool.name,
            "description": tool.description,
            "schema": tool.to_dict(),
            "parameters": tool.schema.parameters if hasattr(tool, 'schema') else {}
        }
    
    def search_tools(self, query: str) -> List[str]:
        """Search for tools by name or description"""
        query_lower = query.lower()
        matching_tools = []
        
        for tool in self.tools:
            if (query_lower in tool.name.lower() or 
                query_lower in tool.description.lower()):
                matching_tools.append(tool.name)
        
        return matching_tools
    
    async def cleanup(self):
        """Clean up resources (close MCP connections)"""
        await self.mcp_adapter.close_all_connections()
    
    def __str__(self) -> str:
        server_count = len(self.connected_servers)
        return f"MCPSimpleAgent({self.name}, tools={len(self.tools)}, servers={server_count})"
    
    def __repr__(self) -> str:
        return self.__str__()


def create_simple_agent(name: str, description: str = "") -> Agent:
    """Create a new simple agent instance"""
    return Agent(name=name, description=description)


async def example_usage():
    """Example of how to use the MCPSimpleAgent"""
    agent = create_simple_agent("MyAgent", "A simple agent with MCP support")
    
    def calculate_square(number: int) -> int:
        """Calculate the square of a number"""
        return number * number
    
    agent.add_function_as_tool("square", "Calculate square of a number", calculate_square)
    
    # Connect to MCP server (example - would need actual server)
    # server_params = StdioServerParameters(command="python", args=["server.py"])
    # await agent.connect_mcp_server("math_server", server_params)
    # await agent.load_tools_from_mcp_server("math_server")
    
    result = agent.execute_tool("square", number=5)
    print(f"Square of 5: {result}")
    
    print(f"Available tools: {agent.list_tools()}")
    
    await agent.cleanup()


if __name__ == "__main__":
    asyncio.run(example_usage())