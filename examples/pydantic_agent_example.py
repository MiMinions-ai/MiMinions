#!/usr/bin/env python3
"""Pydantic Agent Demo"""

import asyncio
import sys
from pathlib import Path

project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from miminions.agent.pydantic_agent import (
    create_pydantic_agent,
    ToolExecutionRequest,
    ExecutionStatus,
)
from mcp import StdioServerParameters


async def basic_usage_example():
    print("Basic Usage")
    
    agent = create_pydantic_agent("PydanticAgent", "A strongly-typed agent")
    
    def add_numbers(a: int, b: int) -> int:
        return a + b
    
    def multiply(a: float, b: float) -> float:
        return a * b
    
    def greet(name: str, formal: bool = False) -> str:
        prefix = "Good day" if formal else "Hello"
        return f"{prefix}, {name}!"
    
    agent.register_tool("add", "Add two integers", add_numbers)
    agent.register_tool("multiply", "Multiply two numbers", multiply)
    agent.register_tool("greet", "Generate a greeting", greet)
    
    print(f"Agent: {agent}")
    print(f"Tools: {agent.list_tools()}")
    print(f"State: {agent.get_state()}")
    
    result = agent.execute("add", a=10, b=5)
    print(f"add(10, 5): {result.status} -> {result.result} ({result.execution_time_ms:.2f}ms)")
    
    result = agent.execute("multiply", a=3.14, b=2.0)
    print(f"multiply(3.14, 2.0): {result.status} -> {result.result} ({result.execution_time_ms:.2f}ms)")
    
    request = ToolExecutionRequest(tool_name="greet", arguments={"name": "Alice", "formal": True})
    result = agent.execute_request(request)
    print(f"Request execution: {result.status} -> {result.result}")
    
    raw_result = agent.execute_tool("add", a=7, b=3)
    print(f"Compatible mode: add(7, 3) = {raw_result}")
    
    await agent.cleanup()
    print("Done")


async def tool_schema_example():
    print("\nTool Schema")
    
    agent = create_pydantic_agent("SchemaAgent")
    
    def search(query: str, max_results: int = 10, include_metadata: bool = False) -> list:
        return [f"Result for: {query}"]
    
    def process_data(data: dict, options: dict = None) -> dict:
        return {"processed": True, "data": data}
    
    agent.register_tool("search", "Search for items", search)
    agent.register_tool("process_data", "Process data", process_data)
    
    schemas = agent.get_tools_schema()
    
    print("Tool schemas:")
    import json
    for schema in schemas:
        print(f"{schema['name']}: {json.dumps(schema['parameters'], indent=2)}")
    
    tool_def = agent.get_tool("search")
    print(f"Definition: {tool_def.name} - {tool_def.description}")
    
    await agent.cleanup()
    print("Done")


async def error_handling_example():
    print("\nError Handling")
    
    agent = create_pydantic_agent("ErrorAgent")
    
    def safe_divide(a: float, b: float) -> float:
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    agent.register_tool("divide", "Divide two numbers", safe_divide)
    
    result = agent.execute("divide", a=10.0, b=2.0)
    print(f"divide(10, 2): {result.status} -> {result.result}")
    
    result = agent.execute("divide", a=10.0, b=0.0)
    print(f"divide(10, 0): {result.status} -> {result.error}")
    
    result = agent.execute("nonexistent", x=1)
    print(f"nonexistent: {result.status} -> {result.error}")
    
    try:
        agent.execute_tool("divide", a=10.0, b=0.0)
    except RuntimeError as e:
        print(f"Exception mode: {e}")
    
    await agent.cleanup()
    print("Done")


async def mcp_integration_example():
    print("\nMCP Integration")
    
    agent = create_pydantic_agent("MCPAgent")
    
    try:
        server_params = StdioServerParameters(command="python3", args=["examples/servers/math_server.py"])
        
        print("Connecting to MCP server")
        await agent.connect_mcp_server("math_server", server_params)
        
        tool_definitions = await agent.load_tools_from_mcp_server("math_server")
        
        print(f"Loaded {len(tool_definitions)} tools: {[t.name for t in tool_definitions]}")
        print(f"All tools: {agent.list_tools()}")
        print(f"State: {agent.get_state()}")
        
        result = await agent.execute_async("add", a=100, b=200)
        print(f"add(100, 200): {result.status} -> {result.result}")
        
        result = await agent.execute_async("multiply", a=7, b=8)
        print(f"multiply(7, 8): {result.status} -> {result.result}")
        
    except Exception as e:
        print(f"Error: {e}")
    
    finally:
        await agent.cleanup()
        print("Done")


async def main():
    print("Pydantic Agent Demonstration")
    
    await basic_usage_example()
    await tool_schema_example()
    await error_handling_example()
    await mcp_integration_example()
    
    print("\nAll demonstrations completed")


if __name__ == "__main__":
    asyncio.run(main())
