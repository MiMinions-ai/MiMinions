"""Agent Test Suite - Core functionality tests."""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent import (
    PydanticAgent,
    create_pydantic_agent,
    ToolDefinition,
    ToolExecutionRequest,
    ToolExecutionResult,
    ExecutionStatus,
    ParameterType,
)


async def test_agent_creation():
    """Test basic agent creation."""
    print("test_agent_creation")
    agent = create_pydantic_agent("TestAgent", "A test agent")
    
    assert agent.name == "TestAgent"
    assert agent.description == "A test agent"
    
    state = agent.get_state()
    assert state.tool_count == 0
    assert state.has_memory == False
    
    await agent.cleanup()
    print("PASSED")
    return True


async def test_tool_registration():
    """Test tool registration and schema extraction."""
    print("test_tool_registration")
    agent = create_pydantic_agent("TestAgent")
    
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
    assert a_param.required == True
    
    tools = agent.list_tools()
    assert "add" in tools
    assert "greet" in tools
    
    await agent.cleanup()
    print("PASSED")
    return True


async def test_tool_execution():
    """Test tool execution styles."""
    print("test_tool_execution")
    agent = create_pydantic_agent("TestAgent")
    
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
    result3 = agent.execute_request(request)
    assert result3.result == 14.0
    
    await agent.cleanup()
    print("PASSED")
    return True


async def test_error_handling():
    """Test error handling."""
    print("test_error_handling")
    agent = create_pydantic_agent("TestAgent")
    
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
    agent = create_pydantic_agent("TestAgent")
    
    def search(query: str, max_results: int = 10) -> list:
        return []
    
    agent.register_tool("search", "Search for items", search)
    
    schemas = agent.get_tools_schema()
    assert len(schemas) == 1
    
    schema = schemas[0]
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
    agent = create_pydantic_agent("TestAgent")
    
    agent.register_tool("math_add", "Add numbers", lambda a, b: a + b)
    agent.register_tool("math_sub", "Subtract numbers", lambda a, b: a - b)
    agent.register_tool("string_concat", "Concatenate strings", lambda a, b: a + b)
    
    math_tools = agent.search_tools("math")
    assert len(math_tools) == 2
    
    assert agent.unregister_tool("math_add") == True
    assert "math_add" not in agent.list_tools()
    assert agent.unregister_tool("nonexistent") == False
    
    await agent.cleanup()
    print("PASSED")
    return True


async def main():
    print("Agent Tests")
    tests = [
        test_agent_creation,
        test_tool_registration,
        test_tool_execution,
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
