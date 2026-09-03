# MCP v2 Compatibility Pin

Date: 2026-09-02

## External Sources

- GitHub Actions failure from PR 122, `test_stdio_server_can_list_tools_and_disconnect_cleanly`.
- MCP v2 migration guide linked by the upstream exception:
  `https://py.sdk.modelcontextprotocol.io/v2/migration/#fastmcp-renamed-to-mcpserver`.

## Direct References

- `pyproject.toml`: MCP dependency constraint.
- `uv.lock`: resolved MCP 1.28.1 in the local environment.
- `tests/integration/tools/test_mcp_stdio_lifecycle.py`: imports
  `mcp.server.fastmcp.FastMCP` in a temporary stdio server.
- `src/miminions/tools/mcp_adapter.py`: MCP client lifecycle under test.

## Finding

CI resolved MCP 2.x from the open-ended `mcp>=1.23.0` constraint. The temporary
server then failed before the adapter could initialize because MCP 2.x removed
`mcp.server.fastmcp.FastMCP` in favor of `mcp.server.mcpserver.MCPServer`.
The adapter reported `MCPError: Connection closed`, which was only a downstream
symptom of the server process exiting.

The local lock resolved MCP 1.28.1, where the test passes unchanged. This is
version drift, not an MCP adapter lifecycle regression.

## Decision

Constrain MCP as `mcp>=1.23.0,<2.0.0` until MiMinions deliberately migrates its
server fixtures and any v1 MCP API usage to the v2 API.

## Validation

- Refreshed `uv.lock` and synced all local extras.
- Focused test: `uv run pytest tests/integration/tools/test_mcp_stdio_lifecycle.py -q`
  passed (1 passed).
- Full suite: `uv run pytest -q` passed (622 passed).
