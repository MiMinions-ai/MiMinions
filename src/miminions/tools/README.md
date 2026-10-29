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
- `create_tool(name, description, func, *, schema=None) -> GenericTool`.
- `GenericTool(..., schema=None)` can accept an explicit dataclass `ToolSchema`.
  Its optional `json_schema` preserves a complete input schema, including nested
  containers, nullable values, and additional-property rules.

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

## Contract

Workspace tools live in the internal `workspace.py` adapter. It builds lazy
callables from AST metadata, validates inputs before approval, and registers via
`create_tool` / `Minion.add_tool`. Metadata search activates at most 32 recent
tools; it never imports code or grants permission. Each invocation uses the
execution service's approval broker, then checks the source digest before import.
Source changes require a new turn and approval. Sync/async calls share a process
lock while import paths and cwd are temporarily configured; these are restored
after execution. Local imports read current source rather than cached bytecode.
Python runs in the current interpreter with OS permissions, without a sandbox.

> [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md) — Contract v2 (optional explicit schemas; additive, no migration).
> **Public surface:** `GenericTool`, `create_tool`, `tool`, `ToolSchema` (dataclass, in `__init__.py`). Invariant: the pydantic `ToolSchema` in `schemas.py` (backing `ToolDefinition`) is a different, internal type — never conflate them.
> **State:** none. **Lifecycle:** typed function → auto-derived JSON schema → agent execution or MCP adaptation (`MCPTool` is async-only).
> **Gate:** tools tests + `scripts/check_structure.py`.

## License

MIT — part of the MiMinions project.
