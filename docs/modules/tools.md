# Tools

The `miminions.tools` module provides a unified interface for defining tools that work across multiple AI frameworks.

## Features

- **Single definition** — write a tool once, export to LangChain, AutoGen, or AGNO
- **Automatic schema** — extracts JSON schema from Python type annotations
- **`@tool` decorator** — clean, declarative syntax
- **MCP adapter** — load tools from any MCP server

## Quick Start

```python
from miminions.tools import tool

@tool(name="calculator", description="Perform basic arithmetic")
def calculate(operation: str, a: int, b: int) -> int:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    return 0

result = calculate.run(operation="add", a=5, b=3)
print(result)  # 8
```

## Using with an Agent

```python
from miminions.agent import create_minion

agent = create_minion("my_agent")
agent.register_tool("calculator", "Perform arithmetic", calculate)
```

Or use the lower-level `Minion` class directly:

```python
from miminions.tools import create_tool
from miminions.agent import Agent

agent = Agent("my_agent", "A helpful agent")
calc = create_tool("calculator", "Perform arithmetic", calculate)
agent.add_tool(calc)
result = agent.execute_tool("calculator", operation="multiply", a=4, b=7)
```

## Framework Adapters

=== "LangChain"
    ```python
    from miminions.tools.langchain_adapter import to_langchain_tool
    lc_tool = to_langchain_tool(calculate)
    result = lc_tool._run(operation="add", a=10, b=5)
    ```

=== "AutoGen"
    ```python
    import asyncio
    from miminions.tools.autogen_adapter import to_autogen_tool
    ag_tool = to_autogen_tool(calculate)
    result = asyncio.run(ag_tool.run({"operation": "subtract", "a": 10, "b": 3}))
    ```

=== "AGNO"
    ```python
    from miminions.tools.agno_adapter import to_agno_tool
    agno_tool = to_agno_tool(calculate)
    result = agno_tool.run(operation="multiply", a=6, b=4)
    ```

## MCP Integration

```python
agent = create_minion("MyAgent")
await agent.load_mcp_tools("path/to/mcp_server.py")
```

## Type Mapping

Python types are automatically converted to JSON Schema types:

| Python | JSON Schema |
|--------|-------------|
| `int` | `"integer"` |
| `float` | `"number"` |
| `bool` | `"boolean"` |
| `str` | `"string"` |
| Other | `"string"` |

## API Reference

### `@tool(name, description)`

Decorator that wraps a function as a `GenericTool`.

### `create_tool(name, description, func) -> GenericTool`

Factory function for creating a tool without the decorator.

### `GenericTool`

| Method/Property | Description |
|-----------------|-------------|
| `run(**kwargs)` | Execute the tool |
| `schema` | JSON schema object |
| `to_dict()` | Schema as a plain dict |
