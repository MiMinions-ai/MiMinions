#!/usr/bin/env python3
"""
Pydantic Agent Test Suite

Comprehensive test suite for the Pydantic Agent implementation, covering:
- Tool registration and execution
- Pydantic model validation
- Schema generation
- Error handling
- Memory integration
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent.pydantic_agent import (
    PydanticAgent,
    create_pydantic_agent,
    ToolDefinition,
    ToolParameter,
    ToolSchema,
    ToolExecutionRequest,
    ToolExecutionResult,
    ExecutionStatus,
    ParameterType,
    AgentConfig,
)


async def test_agent_creation():
    """Test basic agent creation"""
    print("Testing agent creation")
    
    try:
        agent = create_pydantic_agent("TestAgent", "A test agent")
        
        assert agent.name == "TestAgent", f"Expected name 'TestAgent', got '{agent.name}'"
        assert agent.description == "A test agent", f"Description mismatch"
        assert isinstance(agent.config, AgentConfig), "Config should be AgentConfig"
        
        state = agent.get_state()
        assert state.config.name == "TestAgent", "State config name mismatch"
        assert state.tool_count == 0, "Should start with no tools"
        assert state.has_memory == False, "Should start without memory"
        
        await agent.cleanup()
        print("Agent creation test passed")
        return True
        
    except Exception as e:
        print(f"Agent creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_registration():
    """Test tool registration with automatic schema extraction"""
    print("Testing tool registration")
    
    try:
        agent = create_pydantic_agent("ToolRegAgent")
        
        def add(a: int, b: int) -> int:
            """Add two integers"""
            return a + b
        
        def greet(name: str, formal: bool = False) -> str:
            """Greet someone"""
            return f"{'Good day' if formal else 'Hello'}, {name}!"
        
        # Register tools
        add_def = agent.register_tool("add", "Add two numbers", add)
        greet_def = agent.register_tool("greet", "Greet someone", greet)
        
        # Verify tool definitions
        assert isinstance(add_def, ToolDefinition), "Should return ToolDefinition"
        assert add_def.name == "add", "Tool name mismatch"
        assert add_def.description == "Add two numbers", "Description mismatch"
        
        # Verify schema extraction
        add_schema = add_def.schema_def
        assert len(add_schema.parameters) == 2, "Should have 2 parameters"
        
        a_param = next(p for p in add_schema.parameters if p.name == "a")
        assert a_param.type == ParameterType.INTEGER, "Parameter 'a' should be integer"
        assert a_param.required == True, "Parameter 'a' should be required"
        
        # Verify greet has optional parameter
        greet_schema = greet_def.schema_def
        formal_param = next(p for p in greet_schema.parameters if p.name == "formal")
        assert formal_param.required == False, "Parameter 'formal' should be optional"
        assert formal_param.default == False, "Default should be False"
        
        # Verify tool listing
        tools = agent.list_tools()
        assert "add" in tools, "add should be in tools"
        assert "greet" in tools, "greet should be in tools"
        
        await agent.cleanup()
        print("Tool registration test passed")
        return True
        
    except Exception as e:
        print(f"Tool registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_execution_pydantic_style():
    """Test Pydantic-style tool execution"""
    print("Testing Pydantic-style execution")
    
    try:
        agent = create_pydantic_agent("ExecAgent")
        
        def multiply(a: float, b: float) -> float:
            return a * b
        
        agent.register_tool("multiply", "Multiply two numbers", multiply)
        
        # Execute tool
        result = agent.execute("multiply", a=3.0, b=4.0)
        
        assert isinstance(result, ToolExecutionResult), "Should return ToolExecutionResult"
        assert result.status == ExecutionStatus.SUCCESS, f"Expected SUCCESS, got {result.status}"
        assert result.result == 12.0, f"Expected 12.0, got {result.result}"
        assert result.error is None, "Error should be None"
        assert result.execution_time_ms is not None, "Should have execution time"
        assert result.execution_time_ms >= 0, "Execution time should be non-negative"
        
        # Test with arguments dict
        result2 = agent.execute("multiply", arguments={"a": 5.0, "b": 2.0})
        assert result2.result == 10.0, f"Expected 10.0, got {result2.result}"
        
        await agent.cleanup()
        print("Pydantic-style execution test passed")
        return True
        
    except Exception as e:
        print(f"Pydantic-style execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_execution_request():
    """Test execution via ToolExecutionRequest"""
    print("Testing execution request")
    
    try:
        agent = create_pydantic_agent("RequestAgent")
        
        def concat(a: str, b: str) -> str:
            return a + b
        
        agent.register_tool("concat", "Concatenate strings", concat)
        
        # Create request
        request = ToolExecutionRequest(
            tool_name="concat",
            arguments={"a": "Hello, ", "b": "World!"}
        )
        
        # Execute
        result = agent.execute_request(request)
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.result == "Hello, World!"
        assert result.tool_name == "concat"
        
        await agent.cleanup()
        print("Execution request test passed")
        return True
        
    except Exception as e:
        print(f"Execution request test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_simple_agent_compatible_execution():
    """Test Simple Agent compatible execution style"""
    print("Testing Simple Agent compatible execution")
    
    try:
        agent = create_pydantic_agent("CompatAgent")
        
        def subtract(a: int, b: int) -> int:
            return a - b
        
        agent.register_tool("subtract", "Subtract b from a", subtract)
        
        # Use execute_tool (Simple Agent style)
        result = agent.execute_tool("subtract", a=10, b=3)
        assert result == 7, f"Expected 7, got {result}"
        
        # Test add_function_as_tool alias
        def divide(a: float, b: float) -> float:
            return a / b
        
        agent.add_function_as_tool("divide", "Divide a by b", divide)
        result2 = agent.execute_tool("divide", a=10.0, b=2.0)
        assert result2 == 5.0, f"Expected 5.0, got {result2}"
        
        await agent.cleanup()
        print("Simple Agent compatible execution test passed")
        return True
        
    except Exception as e:
        print(f"Simple Agent compatible execution test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling_pydantic_style():
    """Test error handling with Pydantic-style execution"""
    print("Testing Pydantic-style error handling")
    
    try:
        agent = create_pydantic_agent("ErrorAgent")
        
        def failing_tool():
            raise ValueError("This tool always fails")
        
        agent.register_tool("fail", "Always fails", failing_tool)
        
        # Pydantic-style: should not raise, returns error in result
        result = agent.execute("fail")
        
        assert result.status == ExecutionStatus.ERROR, f"Expected ERROR, got {result.status}"
        assert result.error is not None, "Error message should be set"
        assert "This tool always fails" in result.error, "Error message should contain original error"
        assert result.result is None, "Result should be None on error"
        
        # Test nonexistent tool
        result2 = agent.execute("nonexistent")
        assert result2.status == ExecutionStatus.ERROR
        assert "not found" in result2.error.lower()
        
        await agent.cleanup()
        print("Pydantic-style error handling test passed")
        return True
        
    except Exception as e:
        print(f"Pydantic-style error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling_compatible_style():
    """Test error handling with Simple Agent compatible style"""
    print("Testing compatible-style error handling")
    
    try:
        agent = create_pydantic_agent("CompatErrorAgent")
        
        def failing_tool():
            raise ValueError("This tool always fails")
        
        agent.register_tool("fail", "Always fails", failing_tool)
        
        # Compatible-style: should raise exceptions
        try:
            agent.execute_tool("fail")
            assert False, "Should have raised RuntimeError"
        except RuntimeError as e:
            assert "This tool always fails" in str(e)
        
        try:
            agent.execute_tool("nonexistent")
            assert False, "Should have raised ValueError"
        except ValueError as e:
            assert "not found" in str(e).lower()
        
        await agent.cleanup()
        print("Compatible-style error handling test passed")
        return True
        
    except Exception as e:
        print(f"Compatible-style error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_schema_json():
    """Test JSON schema generation for LLM integration"""
    print("Testing JSON schema generation")
    
    try:
        agent = create_pydantic_agent("SchemaAgent")
        
        def search(query: str, max_results: int = 10, fuzzy: bool = False) -> list:
            """Search for items"""
            return []
        
        agent.register_tool("search", "Search for items matching query", search)
        
        # Get schemas
        schemas = agent.get_tools_schema()
        
        assert len(schemas) == 1, f"Expected 1 schema, got {len(schemas)}"
        
        schema = schemas[0]
        assert schema["name"] == "search"
        assert schema["description"] == "Search for items matching query"
        assert "parameters" in schema
        
        params = schema["parameters"]
        assert params["type"] == "object"
        assert "properties" in params
        assert "required" in params
        
        props = params["properties"]
        assert "query" in props
        assert props["query"]["type"] == "string"
        
        assert "max_results" in props
        assert props["max_results"]["type"] == "integer"
        
        assert "fuzzy" in props
        assert props["fuzzy"]["type"] == "boolean"
        
        # Only 'query' should be required
        assert "query" in params["required"]
        assert "max_results" not in params["required"]
        assert "fuzzy" not in params["required"]
        
        await agent.cleanup()
        print("JSON schema generation test passed")
        return True
        
    except Exception as e:
        print(f"JSON schema generation test failed: {e}"))
        import traceback
        traceback.print_exc()
        return False


async def test_custom_schema():
    """Test registration with custom schema"""
    print("Testing custom schema registration")
    
    try:
        agent = create_pydantic_agent("CustomSchemaAgent")
        
        custom_schema = ToolSchema(parameters=[
            ToolParameter(
                name="data",
                type=ParameterType.OBJECT,
                description="The data to process",
                required=True
            ),
            ToolParameter(
                name="format",
                type=ParameterType.STRING,
                description="Output format",
                required=False,
                default="json"
            )
        ])
        
        def process(data: dict, format: str = "json") -> dict:
            return {"data": data, "format": format}
        
        tool_def = agent.register_tool("process", "Process data", process, schema=custom_schema)
        
        # Verify custom schema was used
        assert len(tool_def.schema_def.parameters) == 2
        data_param = next(p for p in tool_def.schema_def.parameters if p.name == "data")
        assert data_param.type == ParameterType.OBJECT
        assert data_param.description == "The data to process"
        
        await agent.cleanup()
        print("Custom schema registration test passed")
        return True
        
    except Exception as e:
        print(f"Custom schema registration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_unregistration():
    """Test tool unregistration"""
    print("Testing tool unregistration")
    
    try:
        agent = create_pydantic_agent("UnregAgent")
        
        def temp_tool() -> str:
            return "temporary"
        
        agent.register_tool("temp", "Temporary tool", temp_tool)
        assert "temp" in agent.list_tools()
        
        # Unregister
        result = agent.unregister_tool("temp")
        assert result == True, "Should return True for successful unregistration"
        assert "temp" not in agent.list_tools()
        
        # Unregister nonexistent
        result2 = agent.unregister_tool("nonexistent")
        assert result2 == False, "Should return False for nonexistent tool"
        
        await agent.cleanup()
        print("Tool unregistration test passed")
        return True
        
    except Exception as e:
        print(f"Tool unregistration test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_search():
    """Test tool search functionality"""
    print("Testing tool search")
    
    try:
        agent = create_pydantic_agent("SearchAgent")
        
        def math_add(a: int, b: int) -> int:
            return a + b
        
        def math_multiply(a: int, b: int) -> int:
            return a * b
        
        def string_concat(a: str, b: str) -> str:
            return a + b
        
        agent.register_tool("math_add", "Add two numbers (math operation)", math_add)
        agent.register_tool("math_multiply", "Multiply two numbers (math operation)", math_multiply)
        agent.register_tool("string_concat", "Concatenate two strings", string_concat)
        
        # Search by name
        math_tools = agent.search_tools("math")
        assert len(math_tools) == 2, f"Expected 2 math tools, got {len(math_tools)}"
        assert "math_add" in math_tools
        assert "math_multiply" in math_tools
        
        # Search by description
        string_tools = agent.search_tools("string")
        assert "string_concat" in string_tools
        
        # Search with no matches
        no_match = agent.search_tools("nonexistent_query_xyz")
        assert len(no_match) == 0
        
        await agent.cleanup()
        print("Tool search test passed")
        return True
        
    except Exception as e:
        print(f"Tool search test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_state():
    """Test agent state tracking"""
    print("Testing agent state")
    
    try:
        agent = create_pydantic_agent("StateAgent", "State test agent")
        
        state1 = agent.get_state()
        assert state1.tool_count == 0
        assert state1.has_memory == False
        assert state1.connected_servers == []
        
        # Add tools
        agent.register_tool("tool1", "Tool 1", lambda: 1)
        agent.register_tool("tool2", "Tool 2", lambda: 2)
        
        state2 = agent.get_state()
        assert state2.tool_count == 2
        
        # Verify config is preserved
        assert state2.config.name == "StateAgent"
        assert state2.config.description == "State test agent"
        
        await agent.cleanup()
        print("Agent state test passed")
        return True
        
    except Exception as e:
        print(f"Agent state test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_execution_timing():
    """Test that execution timing is tracked"""
    print("Testing execution timing")
    
    try:
        import time
        
        agent = create_pydantic_agent("TimingAgent")
        
        def slow_tool() -> str:
            time.sleep(0.05)  # 50ms sleep
            return "done"
        
        agent.register_tool("slow", "A slow tool", slow_tool)
        
        result = agent.execute("slow")
        
        assert result.status == ExecutionStatus.SUCCESS
        assert result.execution_time_ms is not None
        assert result.execution_time_ms >= 50, f"Expected >= 50ms, got {result.execution_time_ms}ms"
        
        await agent.cleanup()
        print("Execution timing test passed")
        return True
        
    except Exception as e:
        print(f"Execution timing test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("Running Pydantic Agent Tests")
    
    tests = [
        test_agent_creation,
        test_tool_registration,
        test_tool_execution_pydantic_style,
        test_tool_execution_request,
        test_simple_agent_compatible_execution,
        test_error_handling_pydantic_style,
        test_error_handling_compatible_style,
        test_tool_schema_json,
        test_custom_schema,
        test_tool_unregistration,
        test_tool_search,
        test_agent_state,
        test_execution_timing,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print(f"\nTests completed: {passed}/{total} passed")
    
    if passed == total:
        print("All tests passed")
        return 0
    else:
        print("Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
