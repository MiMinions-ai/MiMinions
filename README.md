# MiMinions

A Python package for MiMinions that provides a generic tool system for AI frameworks.

## Features

- **Generic Tool System**: Create tools once, use with multiple AI frameworks
- **Framework Adapters**: Support for LangChain, AutoGen, and AGNO
- **Agent Support**: Simple agent class for managing tools
- **Type Safety**: Full type annotation support

## Installation

You can install MiMinions using pip:

```bash
pip install miminions
```

## Quick Start

```python
from miminions.tools import tool
from miminions.agent import Agent

# Create a tool
@tool(name="calculator", description="Simple calculator")
def calculate(operation: str, a: int, b: int) -> int:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    else:
        return 0

# Create an agent and add the tool
agent = Agent("my_agent", "A helpful agent")
agent.add_tool(calculate)

# Use the tool
result = agent.execute_tool("calculator", operation="add", a=5, b=3)
print(result)  # 8

# Convert to different frameworks
langchain_tools = agent.to_langchain_tools()
autogen_tools = agent.to_autogen_tools()
agno_tools = agent.to_agno_tools()
```

## Framework Compatibility

The generic tool system is inter-transferable with:

- **LangChain**: Convert to/from LangChain BaseTool
- **AutoGen**: Convert to/from AutoGen FunctionTool
- **AGNO**: Convert to/from AGNO Function

## Documentation

See `TOOLS_README.md` for detailed documentation of the tool system.

## Examples

Check the `examples/` directory for complete working examples.

## Development

To set up the development environment:

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

