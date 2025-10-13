# MiMinions Examples

This directory contains example programs demonstrating how to use the MiMinions agent system with various features including local function tools and MCP (Model Context Protocol) server integration.

## Overview

The MiMinions agent system allows you to:
- Create simple agents with custom tools
- Add Python functions as tools
- Connect to MCP servers for external tool integration
- Execute tools with proper error handling
- Get tool schemas and information

## Files

### Core Examples

#### `simple_agent_example.py`
The main demonstration script showing both basic and advanced usage patterns.

**Features demonstrated:**
- Basic agent creation and setup
- Adding local Python functions as tools
- MCP server integration
- Tool execution and error handling
- Tool information retrieval

**Key functions:**
- `simple_usage_example()` - Shows the simplest possible usage
- `working_mcp_demo()` - Demonstrates MCP server integration

#### `server.py`
A sample MCP server implementing basic math operations (add, multiply) using FastMCP.

**Tools provided:**
- `add(a: int, b: int) -> int` - Add two numbers
- `multiply(a: int, b: int) -> int` - Multiply two numbers

## Running the Examples

### Prerequisites

1. Make sure you have the required dependencies installed:
   ```bash
   pip install -r requirements.txt
   ```

2. If you encounter import errors, install the package in development mode:
   ```bash
   cd /path/to/MiMinions
   pip install -e .
   ```

### Simple Agent Example

Run the main example script:

```bash
cd /path/to/MiMinions
python examples/simple_agent_example.py
```

This will demonstrate:
- MCP server connection and tool loading
- Local function registration as tools
- Tool execution with both local and MCP tools
- Error handling for missing tools

### MCP Server

The math server can be run standalone for testing:

```bash
cd /path/to/MiMinions
python examples/server.py
```

Note: This server is designed to work with MCP clients via stdio transport.

## Example Usage Patterns

### Basic Agent with Local Tools

```python
from src.miminions.agent.simple_agent import create_simple_agent

# Create agent
agent = create_simple_agent("MyAgent", "A simple agent")

# Add a function as a tool
def add_numbers(x: int, y: int) -> int:
    """Add two numbers"""
    return x + y

agent.add_function_as_tool("add", "Add two numbers", add_numbers)

# Execute tool
result = agent.execute_tool("add", x=5, y=3)
print(f"Result: {result}")  # Output: Result: 8

# Cleanup
await agent.cleanup()
```

### MCP Server Integration

```python
from src.miminions.agent.simple_agent import create_simple_agent
from mcp import StdioServerParameters

# Create agent
agent = create_simple_agent("MCPAgent", "Agent with MCP integration")

# Connect to MCP server
server_params = StdioServerParameters(
    command="python3",
    args=["examples/server.py"]
)

await agent.connect_mcp_server("math_server", server_params)
await agent.load_tools_from_mcp_server("math_server")

# Use MCP tools
result = agent.execute_tool("add", a=10, b=20)
print(f"MCP Result: {result}")  # Output: MCP Result: 30

# Cleanup
await agent.cleanup()
```

### Tool Management

```python
# List available tools
tools = agent.list_tools()
print(f"Available tools: {tools}")

# Search for specific tools
math_tools = agent.search_tools("add")
print(f"Math tools: {math_tools}")

# Get tool information
tool_info = agent.get_tool_info("add")
print(f"Tool info: {tool_info}")

# Get tool schemas (for LLM integration)
schemas = agent.get_tools_schema()
print(f"Schemas: {schemas}")
```

## Error Handling

The examples demonstrate proper error handling for:
- Missing tools
- Tool execution failures
- MCP server connection issues
- Invalid parameters

## Common Issues

### Import Errors
If you get `ModuleNotFoundError: No module named 'src'`, make sure:
1. You're running from the project root directory
2. The `sys.path` is set correctly in the script
3. Or install the package in development mode: `pip install -e .`

### MCP Server Issues
- Ensure the server script is executable and in the correct path
- Check that FastMCP is installed: `pip install fastmcp`
- Verify the server runs independently before using with the agent

## Testing

Run the test suite to verify everything works:

```bash
cd /path/to/MiMinions
python tests/test_simple_agent.py
```

## Legacy Examples

The `legacy/` directory contains older examples and demonstrations that may use different APIs or patterns. These are kept for reference but may not reflect current best practices.
