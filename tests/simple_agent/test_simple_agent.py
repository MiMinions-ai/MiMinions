#!/usr/bin/env python3
"""
Simple Agent Test Suite

Test suite to verify the Simple Agent system works correctly.
"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent.simple_agent import create_simple_agent


async def test_basic_functionality():
    """Test basic agent functionality"""
    print("Testing basic agent functionality...")
    
    try:
        agent = create_simple_agent("TestAgent", "Agent for testing")
        
        def test_add(a: int, b: int) -> int:
            return a + b
        
        def test_greet(name: str) -> str:
            return f"Hello, {name}!"
        
        agent.add_function_as_tool("add", "Add two numbers", test_add)
        agent.add_function_as_tool("greet", "Greet someone", test_greet)
        
        # Test tool execution
        add_result = agent.execute_tool("add", a=5, b=3)
        assert add_result == 8, f"Expected 8, got {add_result}"
        
        greet_result = agent.execute_tool("greet", name="World")
        assert greet_result == "Hello, World!", f"Expected 'Hello, World!', got '{greet_result}'"
        
        # Test tool listing
        tools = agent.list_tools()
        assert "add" in tools, "add tool not found in list"
        assert "greet" in tools, "greet tool not found in list"
        
        # Test tool search
        math_tools = agent.search_tools("add")
        assert "add" in math_tools, "add tool not found in search"
        
        # Test tool info
        add_info = agent.get_tool_info("add")
        assert add_info is not None, "Tool info should not be None"
        assert add_info["name"] == "add", "Tool name mismatch"
        
        await agent.cleanup()
        print("✓ Basic functionality test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Basic functionality test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_schema():
    """Test tool schema generation"""
    print("Testing tool schema generation...")
    
    try:        
        agent = create_simple_agent("SchemaTestAgent")
        
        def complex_function(name: str, age: int, active: bool = True) -> str:
            """A function with multiple parameter types"""
            status = "active" if active else "inactive"
            return f"{name} is {age} years old and {status}"
        
        agent.add_function_as_tool("complex", "Complex function test", complex_function)
        
        schemas = agent.get_tools_schema()
        assert len(schemas) == 1, f"Expected 1 schema, got {len(schemas)}"
        
        schema = schemas[0]
        assert schema["name"] == "complex", "Schema name mismatch"
        assert "parameters" in schema, "Parameters not in schema"
        
        params = schema["parameters"]["properties"]
        assert "name" in params, "name parameter missing"
        assert "age" in params, "age parameter missing"
        assert "active" in params, "active parameter missing"
        
        await agent.cleanup()
        print("✓ Tool schema test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Tool schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_error_handling():
    """Test error handling"""
    print("Testing error handling...")
    
    try:
        agent = create_simple_agent("ErrorTestAgent")
        
        # Test nonexistent tool
        try:
            agent.execute_tool("nonexistent_tool")
            assert False, "Should have raised ValueError"
        except ValueError:
            pass  # Expected
        
        # Test failing tool
        def failing_tool():
            raise RuntimeError("This tool always fails")
        
        agent.add_function_as_tool("fail", "Always fails", failing_tool)
        
        try:
            agent.execute_tool("fail")
            assert False, "Should have raised RuntimeError"
        except RuntimeError:
            pass  # Expected
        
        await agent.cleanup()
        print("✓ Error handling test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Error handling test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_tool_replacement():
    """Test that tools can be replaced"""
    print("Testing tool replacement...")
    
    try:
        agent = create_simple_agent("ReplaceTestAgent")
        
        def add_v1(a: int, b: int) -> int:
            return a + b
        
        def add_v2(a: int, b: int) -> int:
            return (a + b) * 10  # Different behavior
        
        agent.add_function_as_tool("add", "Add v1", add_v1)
        result1 = agent.execute_tool("add", a=1, b=2)
        assert result1 == 3, f"Expected 3, got {result1}"
        
        # Replace with v2
        agent.add_function_as_tool("add", "Add v2", add_v2)
        result2 = agent.execute_tool("add", a=1, b=2)
        assert result2 == 30, f"Expected 30, got {result2}"
        
        # Should only have one 'add' tool
        add_count = sum(1 for t in agent.list_tools() if t == "add")
        assert add_count == 1, f"Expected 1 add tool, got {add_count}"
        
        await agent.cleanup()
        print("✓ Tool replacement test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Tool replacement test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def test_agent_string_representation():
    """Test agent string representation"""
    print("Testing agent string representation...")
    
    try:
        agent = create_simple_agent("StringTestAgent", "Test description")
        
        agent_str = str(agent)
        assert "StringTestAgent" in agent_str, "Agent name not in string"
        assert "tools=" in agent_str, "Tool count not in string"
        
        await agent.cleanup()
        print("✓ Agent string representation test passed!")
        return True
        
    except Exception as e:
        print(f"✗ Agent string representation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


async def main():
    """Run all tests"""
    print("Running Simple Agent Tests")
    print("=" * 50)
    
    tests = [
        test_basic_functionality,
        test_tool_schema,
        test_error_handling,
        test_tool_replacement,
        test_agent_string_representation,
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if await test():
                passed += 1
        except Exception as e:
            print(f"Test {test.__name__} crashed: {e}")
    
    print("\n" + "=" * 50)
    print(f"Tests completed: {passed}/{total} passed")
    
    if passed == total:
        print("✓ All tests passed!")
        return 0
    else:
        print("✗ Some tests failed")
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
