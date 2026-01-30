#!/usr/bin/env python3
"""
Pydantic Agent Demo

This script demonstrates how to use the Pydantic Agent with:
- Tool registration with Pydantic schemas
- Structured execution results
- MCP server integration
"""

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
    """Show the simplest possible usage with Pydantic Agent"""
    print("=== Basic Pydantic Agent Usage ===\n")
    
    agent = create_pydantic_agent("PydanticAgent", "A strongly-typed agent")
    
    # Define tools
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
    
    def multiply(a: float, b: float) -> float:
        """Multiply two numbers"""
        return a * b
    
    def greet(name: str, formal: bool = False) -> str:
        """Generate a greeting"""
        prefix = "Good day" if formal else "Hello"
        return f"{prefix}, {name}!"
    
    # Register tools
    agent.register_tool("add", "Add two integers", add_numbers)
    agent.register_tool("multiply", "Multiply two numbers", multiply)
    agent.register_tool("greet", "Generate a greeting", greet)
    
    print(f"Agent: {agent}")
    print(f"Available tools: {agent.list_tools()}")
    print(f"Agent state: {agent.get_state()}\n")
    
    # Execute using Pydantic-style (returns ToolExecutionResult)
    print("=== Pydantic-style Execution ===")
    
    result = agent.execute("add", a=10, b=5)
    print(f"add(10, 5):")
    print(f"  Status: {result.status}")
    print(f"  Result: {result.result}")
    print(f"  Time: {result.execution_time_ms:.2f}ms\n")
    
    result = agent.execute("multiply", a=3.14, b=2.0)
    print(f"multiply(3.14, 2.0):")
    print(f"  Status: {result.status}")
    print(f"  Result: {result.result}")
    print(f"  Time: {result.execution_time_ms:.2f}ms\n")
    
    # Execute using a request object
    print("=== Request Object Execution ===")
    request = ToolExecutionRequest(
        tool_name="greet",
        arguments={"name": "Alice", "formal": True}
    )
    result = agent.execute_request(request)
    print(f"greet(name='Alice', formal=True):")
    print(f"  Status: {result.status}")
    print(f"  Result: {result.result}\n")
    
    # Execute using Simple Agent compatible style
    print("=== Simple Agent Compatible Execution ===")
    raw_result = agent.execute_tool("add", a=7, b=3)
    print(f"add(7, 3) = {raw_result}\n")
    
    await agent.cleanup()
    print("Basic usage example completed!")


async def tool_schema_example():
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
    
    # Get JSON-serializable schemas (ready for LLM)
    schemas = agent.get_tools_schema()
    
    print("Tool schemas (JSON format for LLM):")
    import json
    for schema in schemas:
        print(f"\n{schema['name']}:")
        print(json.dumps(schema, indent=2))
    
    # Get individual tool definition
    print("\n\nTool definition object:")
    tool_def = agent.get_tool("search")
    print(f"Name: {tool_def.name}")
    print(f"Description: {tool_def.description}")
    print(f"Schema: {tool_def.schema_def}")
    
    await agent.cleanup()
    print("\nTool schema example completed!")


async def error_handling_example():
    """Demonstrate error handling with Pydantic Agent"""
    print("\n=== Error Handling ===\n")
    
    agent = create_pydantic_agent("ErrorAgent")
    
    def safe_divide(a: float, b: float) -> float:
        """Divide a by b"""
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b
    
    agent.register_tool("divide", "Divide two numbers", safe_divide)
    
    # Pydantic-style: Errors returned in result object
    print("Pydantic-style error handling (no exceptions):")
    
    result = agent.execute("divide", a=10.0, b=2.0)
    print(f"divide(10, 2) -> Status: {result.status}, Result: {result.result}")
    
    result = agent.execute("divide", a=10.0, b=0.0)
    print(f"divide(10, 0) -> Status: {result.status}, Error: {result.error}")
    
    result = agent.execute("nonexistent", x=1)
    print(f"nonexistent(x=1) -> Status: {result.status}, Error: {result.error}\n")
    
    # Simple Agent compatible: Raises exceptions
    print("Simple Agent compatible error handling (exceptions):")
    try:
        agent.execute_tool("divide", a=10.0, b=0.0)
    except RuntimeError as e:
        print(f"Caught RuntimeError: {e}")
    
    try:
        agent.execute_tool("nonexistent", x=1)
    except ValueError as e:
        print(f"Caught ValueError: {e}")
    
    await agent.cleanup()
    print("\nError handling example completed!")


async def mcp_integration_example():
    """Demonstrate MCP server integration with Pydantic Agent"""
    print("\n=== MCP Server Integration ===\n")
    
    agent = create_pydantic_agent("MCPAgent", "Pydantic agent with MCP support")
    
    try:
        server_params = StdioServerParameters(
            command="python3",
            args=["examples/servers/math_server.py"]
        )
        
        print("Connecting to MCP math server...")
        await agent.connect_mcp_server("math_server", server_params)
        
        print("Loading tools from MCP server...")
        tool_definitions = await agent.load_tools_from_mcp_server("math_server")
        
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
        
    except Exception as e:
        print(f"MCP demo error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await agent.cleanup()
        print("\nMCP integration example completed!")


async def main():
    """Run all Pydantic Agent demonstrations"""
    print("Pydantic Agent Demonstration")
    print("=" * 60)
    
    await basic_usage_example()
    await tool_schema_example()
    await error_handling_example()
    await mcp_integration_example()
    
    print("\n" + "=" * 60)
    print("All demonstrations completed!")


if __name__ == "__main__":
    asyncio.run(main())
