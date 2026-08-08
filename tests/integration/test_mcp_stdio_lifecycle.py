"""Integration coverage for the real MCP stdio connection lifecycle."""

import sys

import pytest
from mcp import StdioServerParameters

from miminions.tools.mcp_adapter import MCPToolAdapter


@pytest.mark.asyncio
async def test_stdio_server_can_list_tools_and_disconnect_cleanly(tmp_path):
    server_file = tmp_path / "test_mcp_server.py"
    server_file.write_text(
        "\n".join(
            [
                "from mcp.server.fastmcp import FastMCP",
                "server = FastMCP('lifecycle-test')",
                "@server.tool()",
                "def greet(name: str) -> str:",
                "    return f'Hello, {name}!'",
                "if __name__ == '__main__':",
                "    server.run(transport='stdio')",
            ]
        ),
        encoding="utf-8",
    )
    adapter = MCPToolAdapter()

    await adapter.connect_to_server(
        "lifecycle-test",
        StdioServerParameters(command=sys.executable, args=[str(server_file)]),
    )
    tools = await adapter.get_tools_from_server("lifecycle-test")
    await adapter.close_all_connections()

    assert [tool.name for tool in tools] == ["greet"]
    assert adapter.sessions == {}
    assert adapter._connection_tasks == {}
