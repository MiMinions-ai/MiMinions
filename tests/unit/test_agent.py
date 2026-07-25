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


async def test_agent_creation():
    """Test basic agent creation."""
    print("test_agent_creation")
    agent = create_minion("TestAgent", "A test agent")
    
    assert agent.name == "TestAgent"
    assert agent.description == "A test agent"
    
    state = agent.get_state()
    assert state.tool_count == 1
    assert state.has_memory is False
    assert "cli_run_command" in agent.list_tools()
    
    await agent.cleanup()
    print("PASSED")
    return True


async def test_tool_registration():
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
    
    await agent.cleanup()
    print("PASSED")
    return True


async def test_tool_execution():
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
    
    await agent.cleanup()
    print("PASSED")
    return True


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

    assert elapsed < 0.27
    assert [result.result for result in results] == ["first", "second"]
    assert threading.get_ident() not in thread_ids
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

    assert elapsed < 0.2
    assert [result.result for result in results] == ["slow", "fast"]
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

    assert results[0].status == ExecutionStatus.ERROR
    assert results[0].error == "broken tool"
    assert results[1].status == ExecutionStatus.SUCCESS
    assert results[1].result == "ok"
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

        assert [part.tool_name for part in returns] == [
            "work",
            "work",
            "fail_for_model",
        ]
        assert [part.content for part in returns[:2]] == ["first", "second"]
        assert returns[2].content == {
            "status": "error",
            "error": "model-visible failure",
        }
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

    assert reply == "all tools completed"
    assert max_active == 2
    assert model_saw_results is True
    await agent.cleanup()


async def test_error_handling():
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
    
    await agent.cleanup()
    print("PASSED")
    return True


async def test_tool_schema_json():
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
    
    await agent.cleanup()
    print("PASSED")
    return True


async def test_tool_management():
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
    
    await agent.cleanup()
    print("PASSED")
    return True


async def main():
    print("Agent Tests")
    tests = [
        test_agent_creation,
        test_tool_registration,
        test_tool_execution,
        test_parallel_sync_tool_execution,
        test_parallel_async_tools_preserve_request_order,
        test_parallel_batch_isolates_failures,
        test_llm_parallel_results_are_injected_together,
        test_error_handling,
        test_tool_schema_json,
        test_tool_management,
    ]
    
    passed = 0
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"FAILED: {e}")
            import traceback
            traceback.print_exc()
    
    print(f"\nTests completed: {passed}/{len(tests)} passed")
    return 0 if passed == len(tests) else 1


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
