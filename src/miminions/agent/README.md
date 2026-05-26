# MiMinions Agent

Minion agent powered by `pydantic_ai` and OpenRouter.

## Features
- **Async Execution**: The agent owns its full `async run()` reasoning loop.
- **Context Injection**: Use `set_context()` to attach a workspace. When the internal agent is rebuilt, it dynamically builds a system prompt using `ContextBuilder`, feeding the LLM all workspace facts, rules, and global insights before every turn.
- **Tool Registration**: Convert Python functions to tools.
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
