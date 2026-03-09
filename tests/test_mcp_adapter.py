"""
tests/test_mcp_adapter.py

Unit tests for MCPToolAdapter / MCPTool.

Run:
  pytest -vv -s tests/test_mcp_adapter.py
"""

import pytest
from unittest.mock import AsyncMock, MagicMock

from miminions.tools.mcp_adapter import MCPToolAdapter, MCPTool


# -----------------------------
# Fixtures (mock MCP-like objects)
# -----------------------------

@pytest.fixture
def make_mock_result():
    """Factory fixture — call with a list of strings to get a mock MCP result."""
    def _make(texts):
        result = MagicMock()
        result.content = [MagicMock(text=t) for t in texts]
        return result
    return _make


@pytest.fixture
def mock_mcp_tool():
    """Mimics a tool object returned by MCP list_tools()."""
    tool = MagicMock()
    tool.name = "my_tool"
    tool.description = "does stuff"
    tool.model_dump.return_value = {
        "name": "my_tool",
        "description": "does stuff",
        "inputSchema": {
            "type": "object",
            "properties": {"query": {"type": "string"}},
            "required": ["query"],
        },
    }
    return tool


# -----------------------------
# Tests
# -----------------------------

def test_extract_result_single_text_item_returns_string(make_mock_result):
    adapter = MCPToolAdapter()
    out = adapter._extract_result(make_mock_result(["hello"]))
    assert out == "hello"


def test_extract_result_multiple_text_items_returns_list(make_mock_result):
    adapter = MCPToolAdapter()
    out = adapter._extract_result(make_mock_result(["a", "b", "c"]))
    assert out == ["a", "b", "c"]


def test_mcp_tool_to_dict_prefers_input_schema_when_present():
    async def dummy_async(**kwargs):
        return kwargs

    tool = MCPTool(
        name="search",
        description="Search tool",
        func=dummy_async,
        mcp_schema={
            "inputSchema": {
                "type": "object",
                "properties": {"query": {"type": "string"}},
                "required": ["query"],
            }
        },
    )

    d = tool.to_dict()
    assert d["name"] == "search"
    assert d["description"] == "Search tool"
    # Your MCPTool overrides to_dict to return MCP inputSchema as parameters.
    assert d["parameters"]["type"] == "object"
    assert d["parameters"]["properties"]["query"]["type"] == "string"
    assert "query" in d["parameters"].get("required", [])


@pytest.mark.asyncio
async def test_get_tools_from_server_raises_if_server_not_connected():
    adapter = MCPToolAdapter()
    with pytest.raises(ValueError, match="not connected"):
        await adapter.get_tools_from_server("serverA")


@pytest.mark.asyncio
async def test_convert_mcp_tool_to_generic_success_returns_ok_true_and_result(
    make_mock_result, mock_mcp_tool
):
    adapter = MCPToolAdapter()

    # Pretend we have an active connected session
    session = MagicMock()
    session.call_tool = AsyncMock(return_value=make_mock_result(["ok!"]))
    adapter.sessions["serverA"] = session

    tool = await adapter.convert_mcp_tool_to_generic(mock_mcp_tool, "serverA")

    out = await tool.arun(query="hi")
    assert out["ok"] is True
    assert out["result"] == "ok!"
    assert "raw" in out  # raw MCP result returned for debugging


@pytest.mark.asyncio
async def test_convert_mcp_tool_to_generic_error_returns_ok_false_and_error_info():
    adapter = MCPToolAdapter()

    session = MagicMock()
    session.call_tool = AsyncMock(side_effect=RuntimeError("boom"))
    adapter.sessions["serverA"] = session

    mcp_tool = MagicMock()
    mcp_tool.name = "explode"
    mcp_tool.description = "fails"
    mcp_tool.model_dump.return_value = {
        "name": "explode",
        "description": "fails",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    }

    tool = await adapter.convert_mcp_tool_to_generic(mcp_tool, "serverA")

    out = await tool.arun(query="hi")
    assert out["ok"] is False
    assert out["error"]["type"] == "RuntimeError"
    assert "boom" in out["error"]["message"]


@pytest.mark.asyncio
async def test_load_all_tools_from_server_converts_all_tools():
    adapter = MCPToolAdapter()

    t1 = MagicMock()
    t1.name = "t1"
    t1.description = "one"
    t1.model_dump.return_value = {
        "name": "t1",
        "description": "one",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    }

    t2 = MagicMock()
    t2.name = "t2"
    t2.description = "two"
    t2.model_dump.return_value = {
        "name": "t2",
        "description": "two",
        "inputSchema": {"type": "object", "properties": {}, "required": []},
    }

    # Fake list_tools response object
    session = MagicMock()
    session.list_tools = AsyncMock(
        return_value=MagicMock(tools=[t1, t2])
    )
    adapter.sessions["serverA"] = session

    tools = await adapter.load_all_tools_from_server("serverA")
    assert [t.name for t in tools] == ["t1", "t2"]
    assert all(isinstance(t, MCPTool) for t in tools)


def test_mcp_tool_run_raises_async_only_runtime_error():
    async def dummy_async(**kwargs):
        return kwargs

    tool = MCPTool(
        name="async_tool",
        description="async only",
        func=dummy_async,
        mcp_schema={},
    )

    with pytest.raises(RuntimeError, match="async-only"):
        tool.run(x=1)
