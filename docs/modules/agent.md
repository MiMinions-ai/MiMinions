# Agent

The `miminions.agent` module is the core reasoning engine — a **`Minion`** is an async LLM agent built on [pydantic-ai](https://ai.pydantic.dev/) and, by default, [OpenRouter](https://openrouter.ai/). A `Minion` owns the full agent lifecycle: model selection, a tool registry (plain Python functions, `GenericTool` objects, and MCP-server tools), optional [memory](memory.md), optional [workspace context](context.md) injection, and the async `run()` loop.

!!! note "Import from the subpackage"
    Always import from `miminions.agent` — the top-level `import miminions` does not re-export these symbols.

    ```python
    from miminions.agent import create_minion, Minion
    ```

## Features

- **Async execution** — owns its full `async run()` reasoning loop
- **Tool registration** — register plain Python functions or [`GenericTool`](tools.md) objects as LLM-callable tools
- **MCP integration** — connect to Model Context Protocol servers and load their tools
- **Memory** — attach any [memory backend](memory.md) and get 7 memory tools auto-registered
- **Context injection** — attach a [workspace](workspaces.md) and the agent builds a dynamic system prompt via [`ContextBuilder`](context.md) before every turn

## Quick Start

```python
import asyncio
from miminions.agent import create_minion

async def main():
    agent = create_minion("MyAgent")

    def add(a: int, b: int) -> int:
        return a + b

    agent.register_tool("add", "Add two numbers", add)

    reply = await agent.run("What is 3 + 7?")
    print(reply)

asyncio.run(main())
```

!!! warning "Set `OPENROUTER_API_KEY`"
    The default provider is OpenRouter. `run()` needs a working backend, so export `OPENROUTER_API_KEY` first — otherwise the call fails with an auth/network error. For offline runs (tests, examples), use `provider="test"` (see below).

## Model & Provider Selection

`create_minion` defaults to OpenRouter's free `openai/gpt-oss-20b:free` model. Switch providers with `provider=`, or pass a fully-built pydantic-ai model with `model=`.

=== "By provider name"

    ```python
    from miminions.agent import create_minion

    # Default: OpenRouter free model — needs OPENROUTER_API_KEY
    agent = create_minion("MyAgent")

    # Anthropic, OpenAI, or Gemini (each needs its own API key in the env)
    agent = create_minion("MyAgent", provider="anthropic")
    ```

    | `provider` | Default model | Required env var |
    |------------|---------------|------------------|
    | `"openrouter"` (default) | `openai/gpt-oss-20b:free` | `OPENROUTER_API_KEY` |
    | `"openai"` | `gpt-4o` | OpenAI key |
    | `"anthropic"` | `claude-3-5-sonnet-latest` | Anthropic key |
    | `"gemini"` | `gemini-1.5-flash` | Gemini key |
    | `"test"` | `TestModel` (offline) | — |

=== "By explicit model"

    ```python
    from miminions.agent import create_minion
    from pydantic_ai.models.openai import OpenAIModel

    # Pass any pydantic-ai model directly; `model` wins over `provider`
    agent = create_minion("MyAgent", model=OpenAIModel("gpt-4o"))
    ```

=== "Offline (test)"

    ```python
    from miminions.agent import create_minion

    # TestModel runs entirely offline — no API key, no network
    agent = create_minion("MyAgent", provider="test")
    ```

!!! tip "Switching models later"
    Call `agent.set_model(model)` to swap the underlying pydantic-ai model at runtime — it rebuilds the internal agent immediately.

## Registering Tools

A `Minion` can run two flavours of tool. Use `register_tool` for plain functions, or `add_tool` for a [`GenericTool`](tools.md).

```python
from miminions.agent import create_minion
from miminions.tools import tool

agent = create_minion("MyAgent")

# 1. Plain function — schema inferred from the signature
def multiply(a: int, b: int) -> int:
    return a * b

agent.register_tool("multiply", "Multiply two numbers", multiply)

# 2. A GenericTool built with @tool
@tool(name="greet", description="Greet a user by name")
def greet(name: str) -> str:
    return f"Hello, {name}!"

agent.add_tool(greet)

print(agent.list_tools())  # ['multiply', 'greet']
```

See [Tools](tools.md) for `@tool`, `create_tool`, and the `GenericTool` API.

## Attaching Memory

Pass `memory=` at construction, or call `set_memory(...)` later. The moment memory is attached, **7 tools auto-register** so the LLM can read and write memory on its own:

`memory_store`, `memory_recall`, `memory_update`, `memory_delete`, `memory_get`, `memory_list`, and `ingest_document` (chunked PDF/text ingestion).

```python
from miminions.agent import create_minion
from miminions.memory.sqlite import SQLiteMemory  # requires the [sqlite] extra

memory = SQLiteMemory(db_path=":memory:")
agent = create_minion("MyAgent", memory=memory)

# Direct (non-LLM) helpers — both require memory to be attached
entry_id = agent.store_knowledge("MiMinions runs on pydantic-ai.")
hits = agent.recall_knowledge("what does MiMinions run on?", top_k=3)
print(hits[0]["text"])  # result dicts use the key "meta", not "metadata"
```

!!! note
    `store_knowledge` / `recall_knowledge` raise `ValueError("No memory attached")` if no backend is set. `SQLiteMemory` lives in `miminions.memory.sqlite` (not the package top level) and needs `pip install "miminions[sqlite]"`. See [Memory](memory.md) for the full backend reference.

## Attaching a Workspace

Attach a [workspace](workspaces.md) with `set_context(workspace, root_path)`. `WorkspaceManager` requires a **config directory** and you resolve a single workspace with `resolve_workspace` — there is no `get_workspace` method.

```python
from pathlib import Path
from miminions.agent import create_minion
from miminions.core.workspace import WorkspaceManager, resolve_workspace

config_dir = Path.home() / ".miminions"
mgr = WorkspaceManager(config_dir)

# resolve by exact id, id prefix, or exact name
ws = resolve_workspace(mgr.load_workspaces(), "default")

agent = create_minion("MyAgent")
agent.set_context(ws, root_path=config_dir / "workspaces" / f"ws_{ws.id}")
```

Once context is set, a `@agent.system_prompt` callback runs [`ContextBuilder().build(workspace, root_path)`](context.md) on **every** `run()`, injecting identity, prompt files, memory, the workspace graph summary, and a skills index into the system prompt. Call `set_context` before the first `run()` for it to take effect.

!!! note "Builder signature"
    `ContextBuilder().build(workspace, root_path)` takes the workspace and root path as arguments. See [Context Builder](context.md) for the emitted sections.

## Loading MCP Tools

Connect to a [Model Context Protocol](https://modelcontextprotocol.io/) server, then load its tools. The flow is two steps — connect, then load. (MCP needs the optional `mcp` package.)

```python
from mcp import StdioServerParameters
from miminions.agent import create_minion

agent = create_minion("MyAgent")

await agent.connect_mcp_server(
    "filesystem",
    StdioServerParameters(
        command="npx",
        args=["-y", "@modelcontextprotocol/server-filesystem", "/tmp"],
    ),
)

# Register every tool the server exposes
await agent.load_tools_from_mcp_server("filesystem")

print(agent.list_tools())

# Close MCP connections when done
await agent.cleanup()
```

!!! tip
    `await agent.load_tools_from_all_servers()` loads tools from every connected server in one call.

## Executing Tools Directly vs. `run()`

There are three ways to invoke a tool. Pick by how you want errors and results surfaced.

| Method | Returns | On error |
|--------|---------|----------|
| `await run(prompt)` | the LLM's reply (the model decides which tools to call) | re-raises network/API errors |
| `execute(name, arguments=None, **kwargs)` | a `ToolExecutionResult` | **never raises** — failure is captured on the result |
| `execute_tool(name, **kwargs)` | the tool's raw return value | **raises** `ValueError` / `RuntimeError` |

```python
# Let the LLM reason and call tools as needed
reply = await agent.run("Multiply 6 by 7")

# Structured result — inspect .status / .error / .result
from miminions.tools.schemas import ExecutionStatus

res = agent.execute("multiply", {"a": 6, "b": 7})
print(res.result if res.status == ExecutionStatus.SUCCESS else res.error)

# Raw result — raises on missing tool or execution error
value = agent.execute_tool("multiply", a=6, b=7)  # -> 42
```

!!! note "Async tools"
    `execute` / `execute_tool` are synchronous and reject coroutine tools. For async tools use `await execute_async(...)` (structured) or `await execute_tool_async(...)` (raw).

## Multi-turn Conversations

`run()` stores the full message list on `agent._last_messages` after each call. Pass it back as `message_history` to continue a conversation within a session.

```python
reply1 = await agent.run("My name is Asher.")
reply2 = await agent.run("What is my name?", message_history=agent._last_messages)
```

## API Reference

### `create_minion`

```python
create_minion(
    name: str,
    description: str = "",
    memory: BaseMemory | None = None,
    model: Any | None = None,
    provider: str = "openrouter",
) -> Minion
```

Factory that builds a configured `Minion`. When `model` is `None`, `provider` drives model selection (default OpenRouter free model). This is the primary entry point.

### `Minion` methods

| Method | Description |
|--------|-------------|
| `async run(prompt, message_history=None) -> str` | Send a prompt; the model reasons and calls tools. Returns the reply. |
| `register_tool(name, description, func, schema=None) -> ToolDefinition` | Register a Python function as a tool (schema inferred if omitted). |
| `add_tool(tool: GenericTool) -> ToolDefinition` | Register a [`GenericTool`](tools.md). |
| `unregister_tool(name) -> bool` | Remove a tool by name. |
| `list_tools() -> list[str]` | List registered tool names. |
| `search_tools(query) -> list[str]` | Case-insensitive search over tool names/descriptions. |
| `execute(name, arguments=None, **kwargs) -> ToolExecutionResult` | Run a tool synchronously; never raises. |
| `async execute_async(name, arguments=None, **kwargs) -> ToolExecutionResult` | Async variant of `execute`; awaits coroutine tools. |
| `execute_tool(name, **kwargs) -> Any` | Run a tool and return its raw result; raises on error. |
| `async execute_tool_async(name, **kwargs) -> Any` | Async raw-result variant; raises on error. |
| `set_memory(memory) -> None` | Attach a memory backend and auto-register the 7 memory tools. |
| `store_knowledge(text, metadata=None) -> str` | Store text in memory; raises `ValueError` if no memory attached. |
| `recall_knowledge(query, top_k=5) -> list[dict]` | Recall from memory; raises `ValueError` if no memory attached. |
| `set_context(workspace, root_path) -> None` | Attach workspace context for `ContextBuilder` injection on every run. |
| `set_model(model) -> None` | Swap the pydantic-ai model and rebuild the agent. |
| `async connect_mcp_server(name, server_params) -> None` | Connect to an MCP server (`StdioServerParameters`). |
| `async load_tools_from_mcp_server(name) -> list[ToolDefinition]` | Register all tools from a connected server. |
| `async load_tools_from_all_servers() -> list[ToolDefinition]` | Load tools from every connected server. |
| `async cleanup(rebuild=True) -> None` | Close MCP connections (and rebuild the internal agent). |
| `get_state() -> AgentState` | Snapshot: config, tool count, memory flag, connected servers. |

### Properties

| Property | Returns |
|----------|---------|
| `name` | The agent name (`str`). |
| `description` | The agent description (`str`). |
| `memory` | The attached `BaseMemory` or `None`. |

## See Also

<div class="grid cards" markdown>

- :material-database: **[Memory](memory.md)** — vector and markdown memory backends
- :material-file-tree: **[Context Builder](context.md)** — what gets injected into the system prompt
- :material-wrench: **[Tools](tools.md)** — `@tool`, `create_tool`, and `GenericTool`
- :material-graph: **[Workspaces](workspaces.md)** — nodes, rules, and on-disk layout

</div>
