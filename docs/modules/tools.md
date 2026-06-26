# Tools

The `miminions.tools` module turns ordinary Python functions into agent-callable
tools. Annotate a function with the `@tool` decorator (or wrap it with
`create_tool`) and you get a `GenericTool` with an auto-derived JSON schema,
synchronous and asynchronous execution, and a `to_dict()` representation ready
for LLM tool calling. The same package also ships an MCP adapter for pulling
tools off any Model Context Protocol server.

## Features

- **Single definition** — write a plain function, get a typed tool.
- **Automatic schema** — JSON-schema parameters inferred from your type annotations.
- **`@tool` decorator** — clean, declarative syntax.
- **MCP adapter** — load tools from any MCP server and register them on a [Minion](agent.md).

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

# A GenericTool — run it directly:
result = calculate.run(operation="add", a=5, b=3)
print(result)  # 8
```

!!! note "The decorator returns a `GenericTool`, not the original function"
    `@tool(...)` replaces `calculate` with a `GenericTool` instance. Call it
    with `.run(**kwargs)` / `.arun(**kwargs)` rather than `calculate(...)`.
    If you omit `name`/`description`, they default to the function's
    `__name__` and `__doc__`.

## Creating tools

You can build a `GenericTool` two ways — both produce the same object.

=== "`@tool` decorator"
    ```python
    from miminions.tools import tool

    @tool(name="greet", description="Greet a user by name")
    def greet(name: str) -> str:
        return f"Hello, {name}!"

    greet.run(name="Ada")  # "Hello, Ada!"
    ```

=== "`create_tool` factory"
    ```python
    from miminions.tools import create_tool

    def greet(name: str) -> str:
        return f"Hello, {name}!"

    greet_tool = create_tool("greet", "Greet a user by name", greet)
    greet_tool.run(name="Ada")  # "Hello, Ada!"
    ```

## The `GenericTool` API

| Member | Description |
|--------|-------------|
| `run(**kwargs)` | Execute the wrapped function synchronously and return its result. |
| `arun(**kwargs)` | Async execution. Awaits the function if it is a coroutine, otherwise falls back to `run()`. |
| `schema` | A [`ToolSchema`](#toolschema) dataclass with `name`, `description`, `parameters`, and `required`. |
| `to_dict()` | The tool as a JSON-tool-calling dict: `{"name", "description", "parameters": {...}}`. |
| `name` / `description` / `func` | The tool's name, description, and underlying callable. |

```python
@tool(name="calculator", description="Perform basic arithmetic")
def calculate(operation: str, a: int, b: int) -> int:
    ...

calculate.schema.required      # ['operation', 'a', 'b']
calculate.schema.parameters    # {'operation': {'type': 'string', ...}, ...}
calculate.to_dict()
# {
#   'name': 'calculator',
#   'description': 'Perform basic arithmetic',
#   'parameters': {
#     'type': 'object',
#     'properties': {
#       'operation': {'type': 'string', 'description': 'operation'},
#       'a': {'type': 'integer', 'description': 'a'},
#       'b': {'type': 'integer', 'description': 'b'},
#     },
#     'required': ['operation', 'a', 'b'],
#   },
# }
```

A parameter with a default value is treated as optional (omitted from
`required`) and its default is recorded in the schema; a parameter without a
default is required.

## Type Mapping

Parameter types are read from your annotations and converted to JSON Schema
types. Anything that isn't one of the four scalar types below maps to
`"string"`, and an unannotated parameter defaults to `"string"` as well.

| Python | JSON Schema |
|--------|-------------|
| `int` | `"integer"` |
| `float` | `"number"` |
| `bool` | `"boolean"` |
| `str` | `"string"` |
| Other / unannotated | `"string"` |

## Using tools with an agent

Tools become useful once they are attached to a [Minion](agent.md). There are two
registration paths.

=== "Plain function"
    ```python
    from miminions.agent import create_minion

    def calculate(operation: str, a: int, b: int) -> int:
        if operation == "add":
            return a + b
        return a * b

    agent = create_minion("my_agent")
    agent.register_tool("calculator", "Perform arithmetic", calculate)
    ```

=== "`GenericTool`"
    ```python
    from miminions.agent import create_minion
    from miminions.tools import create_tool

    calc = create_tool("calculator", "Perform arithmetic", calculate)

    agent = create_minion("my_agent")
    agent.add_tool(calc)
    ```

Once registered, the tool is available both to the LLM during `await agent.run(...)`
and for direct invocation:

```python
# Raw result, raises on error:
agent.execute_tool("calculator", operation="multiply", a=4, b=7)  # 28

# Structured ToolExecutionResult, never raises:
res = agent.execute("calculator", {"operation": "add", "a": 5, "b": 3})
res.status   # ExecutionStatus.SUCCESS
res.result   # 8

agent.list_tools()  # ['calculator']
```

!!! tip "`register_tool` vs `add_tool`"
    Use `register_tool(name, description, func)` for a bare function — the
    schema is inferred from its signature. Use `add_tool(generic_tool)` when you
    already have a `GenericTool` (e.g. from `@tool` or an MCP server); it
    translates the tool's schema and registers it for you.

## MCP integration

MCP (Model Context Protocol) servers expose tools that a Minion can connect to,
load, and call. The adapter lives in `miminions.tools.mcp_adapter`. In practice
you drive it through the agent: connect to a server, then load its tools.

```python
from mcp import StdioServerParameters
from miminions.agent import create_minion

agent = create_minion("my_agent")

# 1. Connect to an MCP server (here, a stdio server launched as a subprocess)
await agent.connect_mcp_server(
    "files",
    StdioServerParameters(command="python", args=["mcp_server.py"]),
)

# 2. Load its tools — each becomes a registered tool on the agent
await agent.load_tools_from_mcp_server("files")

# 3. The LLM can now call them during a run; or invoke directly (async!)
await agent.execute_tool_async("read_file", path="README.md")

# 4. Close MCP connections when done
await agent.cleanup()
```

Under the hood, `MCPToolAdapter` fetches each MCP tool and wraps it as an
`MCPTool` (a `GenericTool` subclass). You can use the adapter directly for
advanced cases:

```python
from miminions.tools.mcp_adapter import MCPToolAdapter
```

!!! warning "MCP tools are async-only"
    `MCPTool.run()` deliberately **raises** `RuntimeError` so it can never
    return an un-awaited coroutine. Always call MCP tools through `await
    tool.arun(...)`, `await agent.execute_tool_async(...)`, or let the LLM call
    them inside `await agent.run(...)`. MCP support is built in — the `mcp`
    package is a core dependency of `miminions`, so no extra install is needed.

## `ToolSchema`

`GenericTool.schema` returns the public `ToolSchema` **dataclass** from
`miminions.tools`:

```python
from miminions.tools import ToolSchema  # dataclass

# fields: name, description, parameters (dict), required (list[str])
```

!!! note "Two different `ToolSchema` types"
    The public `ToolSchema` exported from `miminions.tools` is a lightweight
    **dataclass**. A separate, internal **pydantic** `ToolSchema` lives in
    `miminions.tools.schemas` and backs the agent's `ToolDefinition`
    machinery. When you work with the public tools API (this page), you mean
    the dataclass. The pydantic one is an implementation detail of the agent's
    tool registry — you generally won't import it directly.

## API Reference

| Symbol | Import | Description |
|--------|--------|-------------|
| `tool(name=None, description=None)` | `from miminions.tools import tool` | Decorator wrapping a function as a `GenericTool`. Name/description default to the function's `__name__`/`__doc__`. |
| `create_tool(name, description, func)` | `from miminions.tools import create_tool` | Factory returning a `GenericTool`. |
| `GenericTool` | `from miminions.tools import GenericTool` | Tool wrapper: `.run(**kwargs)`, async `.arun(**kwargs)`, `.schema`, `.to_dict()`. |
| `ToolSchema` | `from miminions.tools import ToolSchema` | Public schema **dataclass**: `name`, `description`, `parameters`, `required`. |
| `MCPToolAdapter` | `from miminions.tools.mcp_adapter import MCPToolAdapter` | Connects to MCP servers and converts their tools to `GenericTool`s. |
| `MCPTool` | `from miminions.tools.mcp_adapter import MCPTool` | `GenericTool` for an MCP tool — async-only (`run()` raises; use `arun()`). |

See [Agent](agent.md) for registering and running tools, and
[Workspaces](workspaces.md) for how an agent's tool boundary fits into its
runtime context.
