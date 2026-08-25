"""Integration coverage for the real MCP stdio connection lifecycle."""

import sys
import tempfile
from pathlib import Path

import pytest
from mcp import StdioServerParameters

from miminions.tools.mcp_adapter import MCPToolAdapter


@pytest.mark.asyncio
async def test_stdio_server_can_list_tools_and_disconnect_cleanly():
    with tempfile.TemporaryDirectory(dir=Path.cwd()) as temp_dir:
        server_file = Path(temp_dir) / "test_mcp_server.py"
        server_file.write_text(
            """from mcp.server.fastmcp import FastMCP
server = FastMCP('lifecycle-test')
@server.tool()
def greet(name: str) -> str:
    return f'Hello, {name}!'
if __name__ == '__main__':
    server.run(transport='stdio')""",
            encoding="utf-8",
        )
        adapter = MCPToolAdapter()

        await adapter.connect_to_server(
            "lifecycle-test",
            StdioServerParameters(command=sys.executable, args=[str(server_file)]),
        )
        tools = await adapter.get_tools_from_server("lifecycle-test")
        await adapter.close_all_connections()

        tool_names = [tool.name for tool in tools]
        assert tool_names == ["greet"], f"expect MCP stdio lifecycle flow discovers exported tool list as ['greet'], got {tool_names}"
        assert adapter.sessions == {}, f"expect close_all_connections clears active adapter sessions as {{}}, got {adapter.sessions}"
        assert adapter._connection_tasks == {}, f"expect close_all_connections clears pending connection task registry as {{}}, got {adapter._connection_tasks}"
