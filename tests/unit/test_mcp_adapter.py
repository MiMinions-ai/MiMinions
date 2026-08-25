"""
tests/test_mcp_adapter.py

Unit tests for MCPToolAdapter / MCPTool.

Run:
  pytest -vv -s tests/test_mcp_adapter.py
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from miminions.tools.mcp_adapter import MCPTool, MCPToolAdapter

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
    prompt = "hello"
    out = adapter._extract_result(make_mock_result([prompt]))
    assert out == prompt, f"expect the adapter._extract_result to return '{prompt}', got {out}"


def test_extract_result_multiple_text_items_returns_list(make_mock_result):
    adapter = MCPToolAdapter()
    items = ["a", "b", "c"]
    out = adapter._extract_result(make_mock_result(items))
    assert out == items, f"expect the adapter._extract_result to return {items}, got {out}"


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
    assert d["name"] == "search", f"expect the created tool to have name 'search', got {d['name']}"
    assert d["description"] == "Search tool", f"expect the created tool to have description 'Search tool', got {d['description']}"
    # Your MCPTool overrides to_dict to return MCP inputSchema as parameters.
    assert d["parameters"]["type"] == "object", f"expect the parameters type to be 'object', got {d['parameters']['type']}"
    assert d["parameters"]["properties"]["query"]["type"] == "string", f"expect the parameters query type to be 'string', got {d['parameters']['properties']['query']['type']}"
    assert "query" in d["parameters"].get("required", []), f"expect the parameters to contain 'query' in required, got {d['parameters'].get('required', [])}"


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
    assert out["ok"] is True, f"expect after calling tool.arun(), the output['ok'] to be True, got {out['ok']}"
    assert out["result"] == "ok!", f"expect the output['result'] to be 'ok!', got {out['result']}"
    assert "raw" in out, f"expect the output to contain 'raw', got {out}"  # raw MCP result returned for debugging


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
    assert out["ok"] is False, f"expect after calling tool.arun(), the output['ok'] to be False, got {out['ok']}"
    assert out["error"]["type"] == "RuntimeError", f"expect the output['error']['type'] to be 'RuntimeError', got {out['error']['type']}"
    assert "boom" in out["error"]["message"], f"expect the output['error']['message'] to contain 'boom', got {out['error']['message']}"


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
    assert [t.name for t in tools] == ["t1", "t2"], f"expect after calling adapter.load_all_tools_from_server('serverA'), the tool names to be ['t1', 't2'], got {[t.name for t in tools]}"
    assert all(isinstance(t, MCPTool) for t in tools), f"expect all items to be instances of MCPTool, got {[type(t) for t in tools]}"


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


@pytest.mark.asyncio
async def test_connection_contexts_open_and_close_in_their_owner_task():
    adapter = MCPToolAdapter()
    owner_tasks = []

    stdio_context = MagicMock()
    stdio_context.__aenter__ = AsyncMock(return_value=(MagicMock(), MagicMock()))
    stdio_context.__aexit__ = AsyncMock(
        side_effect=lambda *args: owner_tasks.append(asyncio.current_task())
    )
    session = MagicMock()
    session.__aenter__ = AsyncMock(return_value=session)
    session.__aexit__ = AsyncMock(
        side_effect=lambda *args: owner_tasks.append(asyncio.current_task())
    )
    session.initialize = AsyncMock(
        side_effect=lambda: owner_tasks.append(asyncio.current_task())
    )

    with (
        patch('miminions.tools.mcp_adapter.stdio_client', return_value=stdio_context),
        patch('miminions.tools.mcp_adapter.ClientSession', return_value=session),
    ):
        await adapter.connect_to_server("serverA", MagicMock())
        await adapter.close_all_connections()

    assert len(owner_tasks) == 3, f"expect the length of owner_tasks to be 3, got {len(owner_tasks)}"
    assert len(set(owner_tasks)) == 1, f"expect all owner_tasks to be the same, got {len(set(owner_tasks))}"
    assert adapter.sessions == {}, f"expect adapter.sessions to be {{}}, got {adapter.sessions}"
    assert adapter._connection_tasks == {}, f"expect adapter._connection_tasks to be {{}}, got {adapter._connection_tasks}"
