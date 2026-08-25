# MiMinions Agent

Minion agent powered by `pydantic_ai`, defaulting to OpenRouter.

> Full reference: [Agent documentation](https://miminions.ai/modules/agent/).

## Features
- **Async Execution**: The agent owns its full `async run()` reasoning loop.
- **Model/Provider Selection**: Defaults to OpenRouter (`openai/gpt-oss-20b:free`, needs `OPENROUTER_API_KEY`). Pass `provider="openai" | "anthropic" | "gemini" | "test"` or a `pydantic_ai` model via `model=`.
- **Context Injection**: Use `set_context()` to attach a workspace. When the internal agent is rebuilt, it dynamically builds a system prompt using `ContextBuilder`, feeding the LLM all workspace facts, rules, and global insights before every turn.
- **Tool Registration**: Register Python functions as tools with `register_tool()` (or add a `GenericTool` with `add_tool()`).
- **Parallel Tools**: Tool calls emitted together by the model run concurrently. Direct callers can use `execute_many_async()` for the same behavior.
- **Memory Integration**: Pass `memory=SQLiteMemory(...)` to auto-register memory CRUD + `ingest_document` tools.
- **MCP Integration**: Load tools from Model Context Protocol servers.

## Quick Start

```python
import asyncio
from miminions.agent import create_minion

async def main():
    agent = create_minion("MyAgent")
    
    # Attach workspace for Context Injection
    # agent.set_context(workspace, root_path)

    def add(a: int, b: int) -> int:
        return a + b

    agent.register_tool("add", "Add two numbers", add)

    reply = await agent.run("What is 3 + 7?")
    print(reply)

if __name__ == "__main__":
    asyncio.run(main())
```

## Parallel Tool Execution

When the model requests multiple tools in one response, they run concurrently
and their completed results are injected together into the model's next turn.
Synchronous tools use worker threads, while asynchronous tools run directly on
the event loop.

Direct callers can submit a batch of structured requests. Results are returned
in request order, and one failure does not cancel the other tools:

```python
from miminions.tools.schemas import ToolExecutionRequest

results = await agent.execute_many_async([
    ToolExecutionRequest(tool_name="add", arguments={"a": 1, "b": 2}),
    ToolExecutionRequest(tool_name="add", arguments={"a": 3, "b": 4}),
], max_concurrency=16)
```

`max_concurrency` defaults to `16` and must be greater than zero. Lower it for
tools that consume constrained resources such as database connections or file
descriptors.
