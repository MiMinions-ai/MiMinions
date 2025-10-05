# Simple Agent with MCP Server Support

A lightweight, flexible agent system that can dynamically load and use tools from MCP (Model Context Protocol) servers, as well as regular Python functions. This agent provides a unified interface for working with different types of tools and can be easily integrated with various AI frameworks.

## Features

- **Generic Tool Interface**: Unified interface for all tools regardless of their source
- **MCP Server Integration**: Dynamically load tools from MCP servers
- **Python Function Support**: Convert regular Python functions into agent tools
- **Tool Discovery**: Search and discover tools by name or description
- **Framework Adapters**: Convert tools for use with LangChain, AutoGen, and other frameworks
- **Async Support**: Handle both synchronous and asynchronous tool execution

## Quick Start

### Basic Agent Usage

```python
import asyncio
from src.miminions.agent.simple_agent import create_simple_agent

async def basic_example():
    # Create an agent
    agent = create_simple_agent("MyAgent", "A simple demonstration agent")
    
    # Add a Python function as a tool
    def calculate_square(number: int) -> int:
        """Calculate the square of a number"""
        return number * number
    
    agent.add_function_as_tool("square", "Calculate square of a number", calculate_square)
    
    # Use the tool
    result = agent.execute_tool("square", number=5)
    print(f"Square of 5: {result}")  # Output: Square of 5: 25
    
    # List available tools
    print(f"Available tools: {agent.list_tools()}")
    
    # Cleanup
    await agent.cleanup()

# Run the example
asyncio.run(basic_example())
```

### MCP Server Integration

```python
import asyncio
from src.miminions.agent.simple_agent import create_simple_agent
from mcp import StdioServerParameters

async def mcp_example():
    agent = create_simple_agent("MCPAgent", "Agent with MCP server support")
    
    # Connect to an MCP server
    server_params = StdioServerParameters(
        command="python",
        args=["server.py"]  # Your MCP server script
    )
    
    await agent.connect_mcp_server("math_server", server_params)
    
    # Load tools from the server
    await agent.load_tools_from_mcp_server("math_server")
    
    # Use MCP tools just like regular tools
    result = agent.execute_tool("add", a=10, b=20)
    print(f"MCP add result: {result}")
    
    await agent.cleanup()

asyncio.run(mcp_example())
```

## Architecture

### Core Components

1. **GenericTool**: Base interface for all tools
2. **SimpleTool**: Basic implementation for Python functions
3. **MCPTool**: Specialized implementation for MCP server tools
4. **MCPSimpleAgent**: Main agent class with MCP support
5. **MCPToolAdapter**: Handles MCP server communication and tool conversion

### Tool Hierarchy

```
GenericTool (Abstract Base)
├── SimpleTool (Python functions)
├── MCPTool (MCP server tools)
└── Framework-specific tools (LangChain, AutoGen, etc.)
```

## API Reference

### MCPSimpleAgent

The main agent class that manages tools and MCP server connections.

#### Methods

**`__init__(name: str, description: str = "")`**
- Creates a new agent instance

**`async connect_mcp_server(server_name: str, server_params: StdioServerParameters)`**
- Connects to an MCP server

**`async load_tools_from_mcp_server(server_name: str)`**
- Loads all tools from a connected MCP server

**`add_tool(tool: GenericTool)`**
- Adds a generic tool to the agent

**`add_function_as_tool(name: str, description: str, func: callable)`**
- Converts a Python function into a tool and adds it

**`execute_tool(tool_name: str, **kwargs) -> Any`**
- Executes a tool by name with the given arguments

**`list_tools() -> List[str]`**
- Returns a list of all available tool names

**`search_tools(query: str) -> List[str]`**
- Searches for tools by name or description

**`get_tool_info(tool_name: str) -> Optional[Dict[str, Any]]`**
- Gets detailed information about a specific tool

**`async cleanup()`**
- Cleans up resources and closes MCP connections

### GenericTool

Base interface for all tools.

#### Properties

- `name`: Tool name
- `description`: Tool description
- `schema`: Tool parameter schema

#### Methods

**`run(**kwargs) -> Any`**
- Executes the tool with the given arguments

**`to_dict() -> Dict[str, Any]`**
- Converts the tool to a dictionary representation

## Framework Integration

### LangChain

```python
from tools.langchain_adapter import to_langchain_tool

# Convert a generic tool to LangChain format
langchain_tool = to_langchain_tool(agent.get_tool("square"))

# Use with LangChain agents
from langchain.agents import initialize_agent
agent = initialize_agent([langchain_tool], llm, agent_type="zero-shot-react-description")
```

### Creating Custom Framework Adapters

```python
from tools import GenericTool

class MyFrameworkTool:
    def __init__(self, generic_tool: GenericTool):
        self.generic_tool = generic_tool
        self.name = generic_tool.name
        self.description = generic_tool.description
    
    def execute(self, **kwargs):
        return self.generic_tool.run(**kwargs)

def to_my_framework_tool(generic_tool: GenericTool) -> MyFrameworkTool:
    return MyFrameworkTool(generic_tool)
```

## Examples

### Creating an MCP Math Server

```python
# server.py
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    """Multiply two numbers"""
    return a * b

if __name__ == "__main__":
    mcp.run(transport="stdio")
```

### Using the Agent with the Math Server

```python
import asyncio
from agents.mcp_simple_agent import create_simple_agent
from mcp import StdioServerParameters

async def math_agent_example():
    agent = create_simple_agent("MathAgent", "Agent for mathematical operations")
    
    # Connect to math server
    server_params = StdioServerParameters(command="python", args=["server.py"])
    await agent.connect_mcp_server("math", server_params)
    await agent.load_tools_from_mcp_server("math")
    
    # Add custom tools
    def calculate_factorial(n: int) -> int:
        """Calculate factorial of a number"""
        if n <= 1:
            return 1
        return n * calculate_factorial(n - 1)
    
    agent.add_function_as_tool("factorial", "Calculate factorial", calculate_factorial)
    
    # Use tools
    print(f"2 + 3 = {agent.execute_tool('add', a=2, b=3)}")
    print(f"4 * 5 = {agent.execute_tool('multiply', a=4, b=5)}")
    print(f"5! = {agent.execute_tool('factorial', n=5)}")
    
    await agent.cleanup()

asyncio.run(math_agent_example())
```

## Running the Demo

To see the agent in action, run the included demonstration:

```bash
python examples/simple_agent_example.py
```

This will show:
1. Basic agent functionality with Python functions
2. MCP server integration (if available)
3. Tool discovery and search features

## Installation

Make sure you have the required dependencies:

```bash
pip install mcp[cli]
```

For LangChain integration:
```bash
pip install langchain-core
```

## Error Handling

The agent includes comprehensive error handling:

```python
try:
    result = agent.execute_tool("nonexistent_tool", arg=123)
except ValueError as e:
    print(f"Tool not found: {e}")

try:
    result = agent.execute_tool("add", wrong_arg=123)
except RuntimeError as e:
    print(f"Execution error: {e}")
```

## Best Practices

1. **Always call `cleanup()`**: Ensure proper resource cleanup
2. **Handle async properly**: Use `asyncio.run()` for top-level async calls
3. **Check tool existence**: Use `get_tool()` to verify tools exist before execution
4. **Use meaningful names**: Give tools clear, descriptive names
5. **Add proper descriptions**: Include helpful descriptions for tool discovery

## Troubleshooting

### Common Issues

**MCP Server Connection Failed**
- Ensure the server script is correct and executable
- Check that the server parameters (command/args) are valid
- Verify the server implements the MCP protocol correctly

**Tool Execution Errors**
- Check that all required parameters are provided
- Verify parameter types match the tool's expectations
- Use `get_tool_info()` to inspect tool requirements

**Import Errors**
- Ensure all dependencies are installed
- Check Python path and module imports
- Verify the project structure is correct

## Contributing

This is a simple, extensible system. Feel free to:
- Add new framework adapters
- Improve the MCP integration
- Add more tool discovery features
- Enhance error handling and logging

The modular design makes it easy to extend for your specific needs.