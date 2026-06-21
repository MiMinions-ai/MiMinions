# MiMinions Generic Tool Module

Turn ordinary Python functions into agent-callable tools with an auto-derived
JSON schema. Tools work with the `Minion` agent and can also wrap tools loaded
from MCP servers.

> Full reference: [Tools documentation](https://miminions.ai/modules/tools/).

## Quick Start

### Create a tool

```python
from miminions.tools import tool

@tool(name="calculator", description="Simple calculator")
def calculate(operation: str, a: int, b: int) -> int:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    elif operation == "multiply":
        return a * b
    return 0

# @tool returns a GenericTool — call it with .run(), not calculate(...)
result = calculate.run(operation="add", a=5, b=3)   # 8
```

`create_tool(name, description, func)` is the non-decorator equivalent.

### Use a tool with an agent

```python
from miminions.agent import create_minion

agent = create_minion("my_agent")

# A plain function — schema inferred from the signature:
agent.register_tool("calculator", "Perform arithmetic", calculate.func)

# Or add an existing GenericTool:
agent.add_tool(calculate)

# Direct execution (no LLM):
agent.execute_tool("calculator", operation="multiply", a=4, b=7)   # 28
```

During `await agent.run(...)`, the model decides when to call registered tools.

## API

### `GenericTool`

| Member | Description |
|--------|-------------|
| `run(**kwargs)` | Execute synchronously, return the result. |
| `arun(**kwargs)` | Async execution (awaits coroutine functions). |
| `schema` | A `ToolSchema` **dataclass** (`name`, `description`, `parameters`, `required`). |
| `to_dict()` | JSON-tool-calling dict: `{"name", "description", "parameters"}`. |

### Decorator & factory

- `@tool(name=None, description=None)` — wrap a function as a `GenericTool`
  (name/description default to `__name__`/`__doc__`).
- `create_tool(name, description, func) -> GenericTool`.

### Type mapping

`int → "integer"`, `float → "number"`, `bool → "boolean"`, `str → "string"`,
anything else (or unannotated) → `"string"`.

## MCP integration

Load tools from a Model Context Protocol server through the agent:

```python
from mcp import StdioServerParameters
from miminions.agent import create_minion

agent = create_minion("my_agent")
await agent.connect_mcp_server(
    "files", StdioServerParameters(command="python", args=["mcp_server.py"])
)
await agent.load_tools_from_mcp_server("files")
# ...
await agent.cleanup()
```

The adapter lives in `miminions.tools.mcp_adapter` (`MCPToolAdapter`, `MCPTool`).
MCP tools are **async-only** — `MCPTool.run()` raises; use `arun()` or the
agent's async path. The `mcp` package is a core dependency, so no extra install
is required.

## Two `ToolSchema` types

The public `ToolSchema` exported from `miminions.tools` is a lightweight
**dataclass** (returned by `GenericTool.schema`). A separate, internal
**pydantic** `ToolSchema` lives in `miminions.tools.schemas` and backs the
agent's `ToolDefinition` registry. When using the public tools API, you mean the
dataclass.

## License

MIT — part of the MiMinions project.
