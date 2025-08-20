# MiMinions Generic Tool Module

The MiMinions Generic Tool Module provides a unified interface for creating tools that can be used across different AI frameworks including LangChain, AutoGen, and AGNO.

## Features

- **Unified Tool Interface**: Create tools once, use with multiple frameworks
- **Framework Adapters**: Convert between LangChain, AutoGen, and AGNO tool formats
- **Agent Support**: Simple agent class that can manage and execute tools
- **Schema Generation**: Automatic schema extraction from function signatures
- **Type Safety**: Full type annotation support

## Installation

```bash
pip install miminions
```

## Quick Start

### Creating Tools

```python
from miminions.tools import tool

@tool(name="calculator", description="Simple calculator")
def calculate(operation: str, a: int, b: int) -> int:
    """Perform basic arithmetic operations"""
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    elif operation == "divide":
        return a // b if b != 0 else 0
    else:
        return 0

# Use the tool
result = calculate.run(operation="add", a=5, b=3)
print(result)  # 8
```

### Using with Agent

```python
from miminions.agent import Agent

# Create an agent
agent = Agent("my_agent", "A helpful agent")

# Add tools
agent.add_tool(calculate)

# Execute tools through agent
result = agent.execute_tool("calculator", operation="multiply", a=4, b=7)
print(result)  # 28
```

### Framework Compatibility

#### LangChain

```python
from miminions.tools.langchain_adapter import to_langchain_tool

# Convert to LangChain tool
lc_tool = to_langchain_tool(calculate)

# Use with LangChain
result = lc_tool._run(operation="add", a=10, b=5)
print(result)  # 15
```

#### AutoGen

```python
from miminions.tools.autogen_adapter import to_autogen_tool
import asyncio

# Convert to AutoGen tool
ag_tool = to_autogen_tool(calculate)

# Use with AutoGen (async)
async def use_autogen_tool():
    result = await ag_tool.run({"operation": "subtract", "a": 10, "b": 3})
    return result

result = asyncio.run(use_autogen_tool())
print(result)  # 7
```

#### AGNO

```python
from miminions.tools.agno_adapter import to_agno_tool

# Convert to AGNO tool
agno_tool = to_agno_tool(calculate)

# Use with AGNO
result = agno_tool.run(operation="multiply", a=6, b=4)
print(result)  # 24
```

## API Reference

### GenericTool

Base class for all generic tools.

#### Methods

- `run(**kwargs)`: Execute the tool with provided arguments
- `to_dict()`: Get tool schema as dictionary
- `schema`: Get tool schema object

### Agent

Simple agent class for managing and executing tools.

#### Methods

- `add_tool(tool)`: Add a tool to the agent
- `get_tool(name)`: Get a tool by name
- `list_tools()`: List all tool names
- `execute_tool(name, **kwargs)`: Execute a tool by name
- `to_langchain_tools()`: Convert all tools to LangChain format
- `to_autogen_tools()`: Convert all tools to AutoGen format
- `to_agno_tools()`: Convert all tools to AGNO format

### Decorators

#### @tool

Decorator to create a generic tool from a function.

```python
@tool(name="optional_name", description="optional_description")
def my_function(param1: str, param2: int = 0) -> str:
    return f"{param1}: {param2}"
```

### Factory Functions

#### create_tool

Create a generic tool from a function.

```python
from miminions.tools import create_tool

def my_function(x: int) -> int:
    return x * 2

tool = create_tool("doubler", "Doubles a number", my_function)
```

## Type Support

The module automatically converts Python types to appropriate schema types:

- `int` → `"integer"`
- `float` → `"number"`
- `bool` → `"boolean"`
- `str` → `"string"`
- Other types → `"string"` (fallback)

## Examples

See the `examples/` directory for complete working examples.

## Contributing

Contributions are welcome! Please see the GitHub repository for details.

## License

MIT License