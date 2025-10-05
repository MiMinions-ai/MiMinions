# Quick Start Guide: Simple Agent with MCP Support

## Overview

This simple agent system provides a unified interface for working with tools from multiple sources:
- Regular Python functions
- MCP (Model Context Protocol) servers
- Framework-specific tools (LangChain, AutoGen, etc.)

## Installation

1. **Install dependencies:**
   ```bash
   pip install mcp[cli]>=1.15.0
   ```

2. **Optional framework dependencies:**
   ```bash
   # For LangChain integration
   pip install langchain-core
   
   # For other frameworks as needed
   ```

## Basic Usage

### 1. Create an Agent

```python
import asyncio
from agents.mcp_simple_agent import create_simple_agent

async def main():
    # Create agent
    agent = create_simple_agent("MyAgent", "Description of my agent")
    
    # Always remember to cleanup
    await agent.cleanup()

asyncio.run(main())
```

### 2. Add Python Functions as Tools

```python
def calculate_area(width: float, height: float) -> float:
    """Calculate the area of a rectangle"""
    return width * height

# Add to agent
agent.add_function_as_tool("area", "Calculate rectangle area", calculate_area)

# Use the tool
result = agent.execute_tool("area", width=5.0, height=3.0)
print(f"Area: {result}")  # Area: 15.0
```

### 3. Working with MCP Servers

```python
from mcp import StdioServerParameters

async def mcp_example():
    agent = create_simple_agent("MCPAgent")
    
    # Connect to MCP server
    server_params = StdioServerParameters(
        command="python3",
        args=["your_mcp_server.py"]
    )
    
    await agent.connect_mcp_server("my_server", server_params)
    await agent.load_tools_from_mcp_server("my_server")
    
    # Use MCP tools just like regular tools
    # result = agent.execute_tool("mcp_tool_name", param=value)
    
    await agent.cleanup()
```

## Example: Complete Agent Setup

```python
import asyncio
from agents.mcp_simple_agent import create_simple_agent

async def complete_example():
    # Create agent
    agent = create_simple_agent("CompleteAgent", "Agent with multiple tool types")
    
    # Add local Python function tools
    def add_numbers(a: int, b: int) -> int:
        """Add two numbers"""
        return a + b
    
    def greet_user(name: str, formal: bool = False) -> str:
        """Greet a user"""
        greeting = "Good day" if formal else "Hello"
        return f"{greeting}, {name}!"
    
    agent.add_function_as_tool("add", "Add two numbers", add_numbers)
    agent.add_function_as_tool("greet", "Greet someone", greet_user)
    
    # List available tools
    print(f"Available tools: {agent.list_tools()}")
    
    # Execute tools
    sum_result = agent.execute_tool("add", a=10, b=5)
    greet_result = agent.execute_tool("greet", name="Alice", formal=True)
    
    print(f"10 + 5 = {sum_result}")
    print(f"Greeting: {greet_result}")
    
    # Search for tools
    math_tools = agent.search_tools("add")
    print(f"Math tools: {math_tools}")
    
    # Get tool information
    tool_info = agent.get_tool_info("greet")
    print(f"Greet tool info: {tool_info}")
    
    await agent.cleanup()

# Run the example
asyncio.run(complete_example())
```

## Tool Discovery

```python
# List all tools
all_tools = agent.list_tools()

# Search for specific tools
math_tools = agent.search_tools("math")
string_tools = agent.search_tools("string")

# Get detailed tool information
tool_info = agent.get_tool_info("tool_name")
```

## Framework Integration

### LangChain

```python
from tools.langchain_adapter import to_langchain_tool

# Convert agent tool to LangChain format
langchain_tool = to_langchain_tool(agent.get_tool("add"))

# Use with LangChain agents
from langchain.agents import initialize_agent
langchain_agent = initialize_agent([langchain_tool], llm)
```

## Error Handling

```python
try:
    result = agent.execute_tool("add", a=5, b=3)
except ValueError as e:
    print(f"Tool not found: {e}")
except RuntimeError as e:
    print(f"Execution error: {e}")
```

## Best Practices

1. **Always call `cleanup()`** to properly close MCP connections
2. **Use descriptive names** for tools and clear descriptions
3. **Handle errors appropriately** when calling tools
4. **Use type hints** in your tool functions for better schema generation
5. **Test tools individually** before adding to complex workflows

## Testing Your Setup

Run the included test suite:
```bash
python3 test_agent.py
```

Run the demonstration:
```bash
python3 working_demo.py
```

## Troubleshooting

**Import Errors:** Make sure you're running from the project root directory

**MCP Connection Errors:** Verify your MCP server is correctly implemented and the command path is correct

**Tool Execution Errors:** Check that you're providing all required parameters with correct types

## Next Steps

- Explore the framework adapters in the `tools/` directory
- Create your own MCP servers for custom functionality
- Integrate with your preferred AI framework (LangChain, AutoGen, etc.)
- Build more complex multi-agent systems