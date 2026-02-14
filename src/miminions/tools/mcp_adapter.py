"""
MCP Tool Adapter

Connects to MCP servers and converts their tools into MiMinions GenericTool objects.
"""

from typing import Any, Dict, List

from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from . import GenericTool, SimpleTool


class MCPTool(SimpleTool):
    """
    GenericTool wrapper for MCP tools (async-only).

    - Preserves MCP schema (inputSchema) for accurate tool definitions
    - Blocks sync execution (run) to prevent returning coroutine objects silently
    """

    def __init__(self, name: str, description: str, func, mcp_schema: Dict[str, Any]):
        self.mcp_schema = mcp_schema or {}
        super().__init__(name=name, description=description, func=func)

    def run(self, **kwargs):
        raise RuntimeError(
            f"MCP tool '{self.name}' is async-only. "
            f"Use await tool.arun(...) or agent.execute_tool_async(...)."
        )

    def to_dict(self) -> Dict[str, Any]:
        input_schema = self.mcp_schema.get("inputSchema") or {}
        if input_schema:
            return {
                "name": self.name,
                "description": self.description,
                "parameters": input_schema,
            }
        return super().to_dict()


class MCPToolAdapter:
    """
    Adapter to work with MCP servers and convert their tools to GenericTool format.
    """

    def __init__(self):
        self.sessions: Dict[str, ClientSession] = {}
        self.stdio_contexts: Dict[str, Any] = {}

    async def connect_to_server(
        self, server_name: str, server_params: StdioServerParameters
    ) -> None:
        """Connect to an MCP server."""
        stdio_ctx = stdio_client(server_params)
        read, write = await stdio_ctx.__aenter__()
        self.stdio_contexts[server_name] = stdio_ctx

        session = ClientSession(read, write)
        await session.__aenter__()
        await session.initialize()

        self.sessions[server_name] = session

    async def disconnect_server(self, server_name: str) -> None:
        """Disconnect from a specific MCP server."""
        session = self.sessions.pop(server_name, None)
        stdio_ctx = self.stdio_contexts.pop(server_name, None)

        if session:
            await session.__aexit__(None, None, None)
        if stdio_ctx:
            await stdio_ctx.__aexit__(None, None, None)

    async def close_all_connections(self) -> None:
        """Close all MCP server connections."""
        for server_name in list(self.sessions.keys()):
            await self.disconnect_server(server_name)

    async def get_tools_from_server(self, server_name: str) -> List[Any]:
        """Fetch tools from a connected MCP server."""
        if server_name not in self.sessions:
            raise ValueError(f"Server '{server_name}' not connected")

        session = self.sessions[server_name]
        response = await session.list_tools()
        return response.tools if response else []

    def _extract_result(self, result: Any) -> Any:
        """Normalize MCP tool result content."""
        if result and hasattr(result, "content") and result.content:
            items = []
            for item in result.content:
                items.append(item.text if hasattr(item, "text") else item)
            return items[0] if len(items) == 1 else items
        return result

    async def convert_mcp_tool_to_generic(
        self, mcp_tool: Any, server_name: str
    ) -> GenericTool:
        """Convert a single MCP tool to a GenericTool."""
        if hasattr(mcp_tool, "name"):
            tool_name = mcp_tool.name
            tool_description = getattr(mcp_tool, "description", "")
            schema = mcp_tool.model_dump() if hasattr(mcp_tool, "model_dump") else {}
        else:
            tool_name = mcp_tool.get("name", "unknown")
            tool_description = mcp_tool.get("description", "")
            schema = mcp_tool if isinstance(mcp_tool, dict) else {}

        async def mcp_tool_wrapper(**kwargs):
            if server_name not in self.sessions:
                raise ValueError(f"Server '{server_name}' not connected")

            session = self.sessions[server_name]
            try:
                # Prefer MCP signature that accepts named arguments dict
                result = await session.call_tool(tool_name, arguments=kwargs)
                extracted = self._extract_result(result)
                return {"ok": True, "result": extracted, "raw": result}
            except Exception as e:
                return {
                    "ok": False,
                    "error": {
                        "type": type(e).__name__,
                        "message": str(e),
                    },
                }

        return MCPTool(
            name=tool_name,
            description=tool_description,
            func=mcp_tool_wrapper,
            mcp_schema=schema,
        )

    async def load_all_tools_from_server(self, server_name: str) -> List[GenericTool]:
        """Load and convert all tools from an MCP server."""
        mcp_tools = await self.get_tools_from_server(server_name)
        tools: List[GenericTool] = []

        for mcp_tool in mcp_tools:
            tool = await self.convert_mcp_tool_to_generic(mcp_tool, server_name)
            tools.append(tool)

        return tools
