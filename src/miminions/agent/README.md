# MiMinions Agent

Minion agent powered by `pydantic_ai`, defaulting to OpenRouter.

> Full reference: [Agent documentation](https://miminions.ai/modules/agent/).

## Features
- **Async Execution**: The agent owns its full `async run()` reasoning loop.
- **Model/Provider Selection**: Defaults to OpenRouter (`openai/gpt-oss-20b:free`, needs `OPENROUTER_API_KEY`). Pass `provider="openai" | "anthropic" | "gemini" | "test"` or a `pydantic_ai` model via `model=`.
- **Context Injection**: Use `set_context()` to attach a workspace. When the internal agent is rebuilt, it dynamically builds a system prompt using `ContextBuilder`, feeding the LLM all workspace facts, rules, and global insights before every turn.
- **Tool Registration**: Register Python functions as tools with `register_tool()` (or add a `GenericTool` with `add_tool()`).
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
