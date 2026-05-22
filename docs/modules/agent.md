# Agent

The `miminions.agent` module is the core reasoning engine — an async agent powered by [pydantic-ai](https://ai.pydantic.dev/) and [OpenRouter](https://openrouter.ai/).

## Features

- **Async Execution** — owns its full `async run()` reasoning loop
- **Context Injection** — attach a workspace and the agent builds a dynamic system prompt via `ContextBuilder` before every turn
- **Tool Registration** — register Python functions as LLM-callable tools
- **MCP Integration** — load tools directly from Model Context Protocol servers

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

## Attaching a Workspace

```python
from miminions.agent import create_minion
from miminions.core.workspace import WorkspaceManager

agent = create_minion("MyAgent")

manager = WorkspaceManager()
workspace = manager.get_workspace("my_workspace_id")

agent.set_context(workspace, root_path="./my_workspace")
```

When `set_context` is called, `ContextBuilder` assembles all workspace facts, rules, and global memory insights into the system prompt on every LLM call.

## Loading MCP Tools

```python
agent = create_minion("MyAgent")
await agent.load_mcp_tools("path/to/mcp_server.py")
```

## API Reference

### `create_minion(name: str) -> Minion`

Factory function that creates a configured `Minion` instance.

### `Minion`

| Method | Description |
|--------|-------------|
| `async run(prompt)` | Send a prompt and get a reply |
| `register_tool(name, desc, func)` | Register a Python function as a tool |
| `set_context(workspace, root_path)` | Attach a workspace for context injection |
| `async load_mcp_tools(server_path)` | Load tools from an MCP server |
| `list_tools()` | List all registered tool names |
