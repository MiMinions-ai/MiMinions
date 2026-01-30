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
    print("=== Basic Usage ===")
    
    agent = create_pydantic_agent("PydanticAgent", "A strongly-typed agent")
    
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
    
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers"""
        return a * b
    
    def greet(name: str, formal: bool = False) -> str:
        return a + b
    
    def multiply(a: float, b: float) -> float:
        return a * b
    
    def greet(name: str, formal: bool = False) -> str:
    print(f"Available tools: {agent.list_tools()}")
    print(f"Agent state: {agent.get_state()}\n")
        
    result =Tools: {agent.list_tools()}")
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
    print("Done
    """Demonstrate tool schema generation for LLM integration"""
    print("\n=== Tool Schema Generation ===\n")
    
    agent = create_pydantic_agent("SchemaAgent")
    
    def search(query: str, max_results: int = 10, include_metadata: bool = False) -> list:
        """Search for items matching the query"""
        return [f"Result for: {query}"]
    
    def process_data(data: dict, options: dict = None) -> dict:
        """Process data with optional configuration"""
        return {"processed": True, "data": data}
    
    agent.register_tool("search", "Search for items", search)
    agent.register_tool("process_data", "Process data", process_data)
    
    print("=== Tool Schema ===")
    
    agent = create_pydantic_agent("SchemaAgent")
    
    def search(query: str, max_results: int = 10, include_metadata: bool = False) -> list:
        return [f"Result for: {query}"]
    
    def process_data(data: dict, options: dict = None) -> dict:
    print(f"Description: {tool_def.description}")
    print(f"Schema: {tool_def.schema_def}")
    
    await agent.cleanup()
    print("\nTool schema example completed!")


async def error_handlin:")
    import json
    for schema in schemas:
        print(f"{schema['name']}: {json.dumps(schema['parameters'], indent=2)}")
    
    tool_def = agent.get_tool("search")
    print(f"Definition: {tool_def.name} - {tool_def.description}")
    
    await agent.cleanup()
    print("Done
    # Pydantic-style: Errors returned in result object
    print("Pydantic-style error handling (no exceptions):")
    
    result = agent.execute("divide", a=10.0, b=2.0)
    print(f"divide(10, 2) -> Status: {result.status}, Result: {result.result}")
    
    result = agent.execute("divide", a=10.0, b=0.0)
    print("=== Error Handling ===")
    
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
    print("Done
        print(f"Loaded {len(tool_definitions)} tools:")
        for tool_def in tool_definitions:
            print(f"  - {tool_def.name}: {tool_def.description}")
        
        print(f"\nAll available tools: {agent.list_tools()}")
        print(f"Agent state: {agent.get_state()}\n")
        
        # Execute MCP tools asynchronously
        print("Executing MCP tools:")
        result = await agent.execute_async("add", a=100, b=200)
        print(f"MCP add(100, 200) -> Status: {result.status}, Result: {result.result}")
        
        result = await agent.execute_async("multiply", a=7, b=8)
        print(f"MCP multiply(7, 8) -> Status: {result.status}, Result: {result.result}")
        
    print("=== MCP Integration ===")
    
    agent = create_pydantic_agent("MCPAgent")
    
    try:
        server_params = StdioServerParameters(command="python3", args=["examples/servers/math_server.py"])
        
        print("Connecting to MCP server...")
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
        print("Doneprint("Pydantic Agent Demonstration")
    
    await basic_usage_example()
    await tool_schema_example()
    await error_handling_example()
    await mcp_integration_example()
    
    print("All demonstrations completed