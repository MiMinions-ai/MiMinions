"""Agent Test Suite - Core functionality tests."""

import asyncio
import sys
import threading
import time

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
)
from pydantic_ai.models.function import FunctionModel
from unittest.mock import patch

from miminions.agent import (
    create_minion,
)
from miminions.tools.schemas import (
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
    ExecutionStatus,
    ParameterType,
)
from miminions.tools.mcp_adapter import MCPTool


def _cleanup(agent):
    """Close an agent without requiring an async pytest plugin."""
    asyncio.run(agent.cleanup())


def test_agent_creation():
    """Test basic agent creation."""
    print("test_agent_creation")
    agent = create_minion("TestAgent", "A test agent")
    
    assert agent.name == "TestAgent"
    assert agent.description == "A test agent"
    
    state = agent.get_state()
    assert state.tool_count == 1
    assert state.has_memory is False
    assert "cli_run_command" in agent.list_tools()
    
    _cleanup(agent)
    print("PASSED")


def test_tool_registration():
    """Test tool registration and schema extraction."""
    print("test_tool_registration")
    agent = create_minion("TestAgent")
    
    def add(a: int, b: int) -> int:
        return a + b
    
    def greet(name: str, formal: bool = False) -> str:
        return f"{'Good day' if formal else 'Hello'}, {name}!"
    
    add_def = agent.register_tool("add", "Add two numbers", add)
    agent.register_tool("greet", "Greet someone", greet)
    
    # Verify tool definition
    assert isinstance(add_def, ToolDefinition)
    assert add_def.name == "add"
    
    # Verify schema extraction
    a_param = next(p for p in add_def.schema_def.parameters if p.name == "a")
    assert a_param.type == ParameterType.INTEGER
    assert a_param.required is True
    
    tools = agent.list_tools()
    assert "add" in tools
    assert "greet" in tools
    
    _cleanup(agent)
    print("PASSED")


def test_tool_execution():
    """Test tool execution styles."""
    print("test_tool_execution")
    agent = create_minion("TestAgent")
    
    def multiply(a: float, b: float) -> float:
        return a * b
    
    agent.register_tool("multiply", "Multiply two numbers", multiply)
    
    result = agent.execute("multiply", a=3.0, b=4.0)
    assert isinstance(result, ToolExecutionResult)
    assert result.status == ExecutionStatus.SUCCESS
    assert result.result == 12.0
    assert result.execution_time_ms >= 0
    
    # With arguments dict
    result2 = agent.execute("multiply", arguments={"a": 5.0, "b": 2.0})
    assert result2.result == 10.0
    
    # Raw execution (returns value directly)
    raw = agent.execute_tool("multiply", a=2.0, b=3.0)
    assert raw == 6.0
    
    # Via ToolExecutionRequest
    request = ToolExecutionRequest(tool_name="multiply", arguments={"a": 7.0, "b": 2.0})
    result3 = agent.handle_tool_execution_request(request)
    assert result3.result == 14.0
    
    _cleanup(agent)
    print("PASSED")


async def test_parallel_sync_tool_execution():
    """Blocking synchronous tools run concurrently in worker threads."""
    agent = create_minion("TestAgent", provider="test")
    thread_ids = set()

    def slow_value(value: str, delay: float) -> str:
        thread_ids.add(threading.get_ident())
        time.sleep(delay)
        return value

    agent.register_tool("slow_value", "Return a value slowly", slow_value)
    requests = [
        ToolExecutionRequest(
            tool_name="slow_value",
            arguments={"value": value, "delay": 0.15},
        )
        for value in ("first", "second")
    ]

    started = time.perf_counter()
    results = await agent.execute_many_async(requests)
    elapsed = time.perf_counter() - started

    actual_values = [result.result for result in results]
    assert elapsed < 0.27, f"Expected elapsed time under 0.27s, got {elapsed:.3f}s"
    assert actual_values == ["first", "second"], (
        f"Expected ordered results ['first', 'second'], got {actual_values!r}"
    )
    assert threading.get_ident() not in thread_ids, (
        f"Expected worker thread IDs, got main thread in {thread_ids!r}"
    )
    await agent.cleanup()


async def test_parallel_async_tools_preserve_request_order():
    """Async tools overlap while results remain in request order."""
    agent = create_minion("TestAgent", provider="test")

    async def delayed(value: str, delay: float) -> str:
        await asyncio.sleep(delay)
        return value

    agent.register_tool("delayed", "Return a delayed value", delayed)
    requests = [
        ToolExecutionRequest(
            tool_name="delayed",
            arguments={"value": "slow", "delay": 0.12},
        ),
        ToolExecutionRequest(
            tool_name="delayed",
            arguments={"value": "fast", "delay": 0.01},
        ),
    ]

    started = time.perf_counter()
    results = await agent.execute_many_async(requests)
    elapsed = time.perf_counter() - started

    actual_values = [result.result for result in results]
    assert elapsed < 0.2, f"Expected elapsed time under 0.2s, got {elapsed:.3f}s"
    assert actual_values == ["slow", "fast"], (
        f"Expected ordered results ['slow', 'fast'], got {actual_values!r}"
    )
    await agent.cleanup()


async def test_parallel_batch_respects_concurrency_limit():
    """Batch execution never exceeds its configured concurrency limit."""
    agent = create_minion("TestAgent", provider="test")
    active = 0
    max_active = 0

    async def track_concurrency(value: int) -> int:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.03)
        active -= 1
        return value

    agent.register_tool(
        "track_concurrency",
        "Track active executions",
        track_concurrency,
    )
    requests = [
        ToolExecutionRequest(
            tool_name="track_concurrency",
            arguments={"value": value},
        )
        for value in range(6)
    ]

    results = await agent.execute_many_async(requests, max_concurrency=2)
    actual_values = [result.result for result in results]

    assert max_active == 2, f"Expected at most 2 active tools, got {max_active}"
    assert actual_values == list(range(6)), (
        f"Expected ordered results {list(range(6))!r}, got {actual_values!r}"
    )
    await agent.cleanup()


async def test_parallel_batch_rejects_invalid_concurrency_limit():
    """A non-positive concurrency limit is rejected clearly."""
    agent = create_minion("TestAgent", provider="test")

    try:
        await agent.execute_many_async([], max_concurrency=0)
        assert False, "Expected ValueError, got no exception"
    except ValueError as exc:
        actual_message = str(exc)
        assert actual_message == "max_concurrency must be greater than zero", (
            "Expected max_concurrency validation error, "
            f"got {actual_message!r}"
        )

    await agent.cleanup()


async def test_parallel_batch_isolates_failures():
    """A failed request does not cancel successful siblings."""
    agent = create_minion("TestAgent", provider="test")

    def fail() -> None:
        raise ValueError("broken tool")

    async def succeed() -> str:
        await asyncio.sleep(0)
        return "ok"

    agent.register_tool("fail", "Fail", fail)
    agent.register_tool("succeed", "Succeed", succeed)

    results = await agent.execute_many_async([
        ToolExecutionRequest(tool_name="fail"),
        ToolExecutionRequest(tool_name="succeed"),
    ])

    assert results[0].status == ExecutionStatus.ERROR, (
        f"Expected first status error, got {results[0].status!r}"
    )
    assert results[0].error == "broken tool", (
        f"Expected error 'broken tool', got {results[0].error!r}"
    )
    assert results[1].status == ExecutionStatus.SUCCESS, (
        f"Expected second status success, got {results[1].status!r}"
    )
    assert results[1].result == "ok", (
        f"Expected successful result 'ok', got {results[1].result!r}"
    )
    await agent.cleanup()


async def test_llm_parallel_results_are_injected_together():
    """The model receives all concurrently completed tool results at once."""
    model_saw_results = False

    def model_handler(messages, _info):
        nonlocal model_saw_results
        returns = [
            part
            for message in messages
            if isinstance(message, ModelRequest)
            for part in message.parts
            if isinstance(part, ToolReturnPart)
        ]
        if not returns:
            return ModelResponse(parts=[
                ToolCallPart("work", {"value": "first"}),
                ToolCallPart("work", {"value": "second"}),
                ToolCallPart("fail_for_model", {}),
            ])

        actual_tool_names = [part.tool_name for part in returns]
        expected_tool_names = [
            "work",
            "work",
            "fail_for_model",
        ]
        assert actual_tool_names == expected_tool_names, (
            f"Expected tool returns {expected_tool_names!r}, got {actual_tool_names!r}"
        )
        actual_success_content = [part.content for part in returns[:2]]
        assert actual_success_content == ["first", "second"], (
            "Expected successful content ['first', 'second'], "
            f"got {actual_success_content!r}"
        )
        expected_error_content = {
            "status": "error",
            "error": "model-visible failure",
        }
        assert returns[2].content == expected_error_content, (
            f"Expected error content {expected_error_content!r}, "
            f"got {returns[2].content!r}"
        )
        model_saw_results = True
        return ModelResponse(parts=[TextPart("all tools completed")])

    agent = create_minion("TestAgent", model=FunctionModel(model_handler))
    active = 0
    max_active = 0

    async def work(value: str) -> str:
        nonlocal active, max_active
        active += 1
        max_active = max(max_active, active)
        await asyncio.sleep(0.05)
        active -= 1
        return value

    def fail_for_model() -> None:
        raise ValueError("model-visible failure")

    agent.register_tool("work", "Do asynchronous work", work)
    agent.register_tool("fail_for_model", "Fail visibly", fail_for_model)

    reply = await agent.run("Run all tools")

    assert reply == "all tools completed", (
        f"Expected final reply 'all tools completed', got {reply!r}"
    )
    assert max_active == 2, f"Expected 2 concurrent LLM tools, got {max_active}"
    assert model_saw_results is True, (
        f"Expected model_saw_results True, got {model_saw_results!r}"
    )
    await agent.cleanup()


def test_error_handling():
    """Test error handling."""
    print("test_error_handling")
    agent = create_minion("TestAgent")
    
    def failing_tool():
        raise ValueError("This tool always fails")
    
    agent.register_tool("fail", "Always fails", failing_tool)
    
    # execute() captures errors
    result = agent.execute("fail")
    assert result.status == ExecutionStatus.ERROR
    assert "always fails" in result.error.lower()
    
    # execute() on nonexistent tool
    result2 = agent.execute("nonexistent")
    assert result2.status == ExecutionStatus.ERROR
    assert "not found" in result2.error.lower()
    
    # execute_tool() raises exceptions
    try:
        agent.execute_tool("fail")
        assert False, "Should have raised"
    except RuntimeError:
        pass
    
    _cleanup(agent)
    print("PASSED")


def test_tool_schema_json():
    """Test JSON schema generation."""
    print("test_tool_schema_json")
    agent = create_minion("TestAgent")
    
    def search(query: str, max_results: int = 10) -> list:
        return []
    
    agent.register_tool("search", "Search for items", search)
    
    schemas = agent.get_tools_schema()
    assert len(schemas) == 2
    
    schema = next(s for s in schemas if s["name"] == "search")
    assert schema["name"] == "search"
    assert "parameters" in schema
    assert "query" in schema["parameters"]["properties"]
    assert "query" in schema["parameters"]["required"]
    assert "max_results" not in schema["parameters"]["required"]
    
    _cleanup(agent)
    print("PASSED")


def test_command_tool_schema_hides_permission_policy():
    """The model-facing command tool cannot provide its own policy."""
    agent = create_minion("TestAgent")

    schema = next(
        item for item in agent.get_tools_schema()
        if item["name"] == "cli_run_command"
    )
    properties = schema["parameters"]["properties"]
    assert "command" in properties
    assert "timeout" in properties
    assert "policy" not in properties

    _cleanup(agent)
    print("PASSED")


def test_command_tool_uses_subprocess_reported_timing():
    """Command approval time is not included in the agent execution duration."""
    agent = create_minion("TestAgent")

    class TimedResult(dict):
        execution_time_ms = 12.5

    agent._tools["cli_run_command"].func = lambda **kwargs: TimedResult(
        returncode=0,
        stdout="",
        stderr="",
    )
    result = agent.execute("cli_run_command", command="python --version")

    assert result.execution_time_ms == 12.5
    _cleanup(agent)


def test_rejected_command_reports_zero_execution_time():
    """Time waiting for a rejected confirmation is not execution time."""
    agent = create_minion("TestAgent")

    with patch("miminions.tools.default.click.confirm", return_value=False):
        result = agent.execute("cli_run_command", command="python --version")

    assert result.status == ExecutionStatus.ERROR
    assert "not approved" in result.error
    assert result.execution_time_ms == 0.0
    _cleanup(agent)


def test_tool_management():
    """Test tool search and unregistration."""
    print("test_tool_management")
    agent = create_minion("TestAgent")
    
    agent.register_tool("math_add", "Add numbers", lambda a, b: a + b)
    agent.register_tool("math_sub", "Subtract numbers", lambda a, b: a - b)
    agent.register_tool("string_concat", "Concatenate strings", lambda a, b: a + b)
    
    math_tools = agent.search_tools("math")
    assert len(math_tools) == 2
    
    assert agent.unregister_tool("math_add") is True
    assert "math_add" not in agent.list_tools()
    assert agent.unregister_tool("nonexistent") is False
    
    _cleanup(agent)
    print("PASSED")


async def test_async_generic_tool_registration_uses_async_execution_and_schema():
    """Async-backed GenericTools such as MCP tools must not use sync run()."""
    agent = create_minion("TestAgent")

    async def greet(**kwargs):
        return f"Hello, {kwargs['name']}!"

    tool = MCPTool(
        name="greet",
        description="Return a greeting.",
        func=greet,
        mcp_schema={
            "inputSchema": {
                "type": "object",
                "properties": {"name": {"type": "string"}},
                "required": ["name"],
            }
        },
    )
    agent.add_tool(tool)

    result = await agent.execute_async("greet", arguments={"name": "MiMinions"})

    assert result.status == ExecutionStatus.SUCCESS
    assert result.result == "Hello, MiMinions!"
    info = agent.get_tool_info("greet")
    assert info["parameters"]["properties"]["name"]["type"] == "string"
    assert "name" in info["parameters"]["required"]
    await agent.cleanup()


async def main():
    print("Agent Tests")
    tests = [
        test_agent_creation,
        test_tool_registration,
        test_tool_execution,
        test_parallel_sync_tool_execution,
        test_parallel_async_tools_preserve_request_order,
        test_parallel_batch_respects_concurrency_limit,
        test_parallel_batch_rejects_invalid_concurrency_limit,
        test_parallel_batch_isolates_failures,
        test_llm_parallel_results_are_injected_together,
        test_error_handling,
        test_tool_schema_json,
        test_command_tool_schema_hides_permission_policy,
        test_command_tool_uses_subprocess_reported_timing,
        test_rejected_command_reports_zero_execution_time,
        test_tool_management,
    ]
    
    passed = 0
    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nTests completed: {passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(main())
