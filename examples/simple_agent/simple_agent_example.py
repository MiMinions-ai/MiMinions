#!/usr/bin/env python3
"""
Simple Agent Demo

This script demonstrates how to use the Simple Agent with both local Python
functions and MCP server integration.
"""

import asyncio

from miminions.agent.simple_agent import create_simple_agent
from mcp import StdioServerParameters


async def working_mcp_demo():
    """Demonstrate working MCP integration"""
    print("Working MCP Demo")
    
    agent = create_simple_agent("WorkingMCPAgent", "Agent with working MCP integration")
    
    try:
        server_params = StdioServerParameters(
            command="python3",
            args=["examples/servers/math_server.py"]
        )
        
        print("Connecting to MCP math server")
        await agent.connect_mcp_server("math_server", server_params)
        
        print("Loading tools from MCP server")
        await agent.load_tools_from_mcp_server("math_server")
        
        print(f"Available tools: {agent.list_tools()}")
        
        def power(base: int, exponent: int) -> int:
            """Calculate base raised to the power of exponent"""
            return base ** exponent
        
        def factorial(n: int) -> int:
            """Calculate factorial of n"""
            if n <= 1:
                return 1
            return n * factorial(n - 1)
        
        agent.add_function_as_tool("power", "Calculate power", power)
        agent.add_function_as_tool("factorial", "Calculate factorial", factorial)
        
        print(f"All tools after adding local ones: {agent.list_tools()}")
        
        print("\nTool Execution Results")
        
        print(f"power(2, 8) = {agent.execute_tool('power', base=2, exponent=8)}")
        print(f"factorial(5) = {agent.execute_tool('factorial', n=5)}")
        
        try:
            result = await agent.execute_tool_async("add", a=15, b=25)
            print(f"MCP add(15, 25) = {result}")
        except Exception as e:
            print(f"MCP add failed: {e}")
        
        try:
            result = await agent.execute_tool_async("multiply", a=6, b=9)
            print(f"MCP multiply(6, 9) = {result}")
        except Exception as e:
            print(f"MCP multiply failed: {e}")
        
        print("\nTool Information")
        for tool_name in agent.list_tools():
            info = agent.get_tool_info(tool_name)
            if info:
                print(f"{tool_name}: {info['description']}")
        
    except Exception as e:
        print(f"Demo error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        await agent.cleanup()
        print("\nDone")


async def simple_usage_example():
    """Show the simplest possible usage"""
    print("\nSimple Usage Example")
    
    agent = create_simple_agent("SimpleAgent")
    
    def add_numbers(x: int, y: int) -> int:
        """Add two numbers"""
        return x + y
    
    def get_greeting(name: str) -> str:
        """Get a personalized greeting"""
        return f"Hello, {name}! Welcome to the Simple Agent system."
    
    agent.add_function_as_tool("add", "Add two numbers", add_numbers)
    agent.add_function_as_tool("greet", "Get greeting", get_greeting)
    
    print(f"Available tools: {agent.list_tools()}")
    print(f"2 + 3 = {agent.execute_tool('add', x=2, y=3)}")
    print(f"Greeting: {agent.execute_tool('greet', name='User')}")
    
    await agent.cleanup()
    print("Done")


async def main():
    """Run the working demo"""
    print("Working MCP Agent Demonstration")
    
    await working_mcp_demo()
    await simple_usage_example()
    
    print("\nAll demonstrations completed")

if __name__ == "__main__":
    asyncio.run(main())
