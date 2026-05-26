# MiMinions

An agentic framework for multi-agent systems with knowledge retrieval, long-term memory, and MCP server support — built on [pydantic-ai](https://ai.pydantic.dev/) and [OpenRouter](https://openrouter.ai/).

## Features

- **Minion Agent** — async reasoning loop powered by pydantic-ai and OpenRouter
- **Long-Term Memory** — three-tier memory system (session logs, workspace facts, global insights)
- **Context Injection** — workspace state and memory automatically injected into every LLM call
- **Generic Tool System** — create tools once, use with LangChain, AutoGen, and AGNO
- **MCP Integration** — load tools directly from Model Context Protocol servers
- **CLI & Chat** — interactive chat with session resumption and background memory distillation
- **Vector Search** — SQLite-backed vector memory with keyword and full-text search

## Quick Install

```bash
pip install miminions
```

For optional SQLite vector memory:

```bash
pip install miminions[sqlite]
```

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

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       CLI / Chat                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      Minion Agent                           │
│           (pydantic-ai + OpenRouter + MCP)                  │
└──────────┬──────────────┬───────────────────┬───────────────┘
           │              │                   │
    ┌──────▼──────┐ ┌─────▼──────┐ ┌─────────▼────────┐
    │    Tools    │ │   Memory   │ │ Context Builder  │
    │  (Generic,  │ │ (3-tier:   │ │ (prompt assembly │
    │  MCP, LLM)  │ │ MD+SQLite) │ │  from workspace) │
    └─────────────┘ └────────────┘ └──────────────────┘
```

See the [Getting Started](getting-started.md) guide to set up your first agent.
