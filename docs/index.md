---
hide:
  - navigation
  - toc
---

<div class="home-hero" markdown>

# Build Autonomous AI Agents with MiMinions

The open-source framework for creating, deploying, and managing agentic AI systems at scale — built on [pydantic-ai](https://ai.pydantic.dev/) and [OpenRouter](https://openrouter.ai/).

[Get Started](getting-started.md){ .md-button .md-button--primary }
[Explore Features](features.md){ .md-button }
[:fontawesome-brands-github: GitHub](https://github.com/MiMinions-ai/MiMinions){ .md-button }

</div>

## Key Features

<div class="grid cards" markdown>

-   :material-robot:{ .lg .middle } &nbsp; **Autonomous Agents**

    ---

    Create AI agents that think, plan, and execute tasks independently through
    an async reasoning loop powered by pydantic-ai and OpenRouter.

-   :material-graph-outline:{ .lg .middle } &nbsp; **Multi-Agent Systems**

    ---

    Build complex systems where multiple agents collaborate, share context, and
    coordinate to solve problems no single agent could.

-   :material-brain:{ .lg .middle } &nbsp; **Three-Tier Memory**

    ---

    Session logs, stable workspace facts, and a global vector store keep agents
    context-aware across conversations and workspaces.

-   :material-connection:{ .lg .middle } &nbsp; **MCP Integration**

    ---

    Connect to Model Context Protocol servers and load their tools directly into
    an agent, right alongside your own custom Python functions.

-   :material-tools:{ .lg .middle } &nbsp; **Generic Tool System**

    ---

    Define a tool once from a typed Python function and get a framework-agnostic
    JSON schema for free — then hand it to any agent or load tools from MCP
    servers.

-   :material-magnify:{ .lg .middle } &nbsp; **Vector Search**

    ---

    SQLite-backed vector memory with semantic, keyword, and full-text search for
    fast, relevant retrieval.

</div>

## Get Started with MiMinions

Build powerful autonomous AI agents that understand complex tasks, make
decisions, and execute actions with minimal human intervention. Everything you
need to create intelligent systems that scale — in a few lines of code.

### Why choose MiMinions?

- :material-check-circle:{ .middle } **Rapid development** — get started in minutes with an intuitive API
- :material-check-circle:{ .middle } **Production ready** — built for scale with reliable, tested internals
- :material-check-circle:{ .middle } **Flexible architecture** — customise agents to fit your unique needs
- :material-check-circle:{ .middle } **Open source** — join the community and shape the future of agentic AI

### Quick start

Install the framework:

```bash
pip install miminions
```

The default OpenRouter backend needs an API key. Set it once in your environment:

```bash
export OPENROUTER_API_KEY="your-key-here"
```

Create your first agent:

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

!!! tip "Working offline?"
    Pass `provider="test"` to `create_minion` to use pydantic-ai's `TestModel`
    and run without any API key — handy for tests and experiments.

Then head to the [Getting Started](getting-started.md) guide to go further.

## Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                       CLI / Chat                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      Minion Agent                           │
│        (pydantic-ai + OpenRouter + MCP servers)             │
└──────┬──────────────┬──────────────┬──────────────┬─────────┘
       │              │              │              │
 ┌─────▼─────┐ ┌──────▼─────┐ ┌──────▼──────┐ ┌─────▼──────┐
 │   Tools   │ │   Memory   │ │   Context   │ │ Workspaces │
 │ (Generic, │ │ (MD files  │ │   Builder   │ │  (nodes,   │
 │   MCP)    │ │ + SQLite)  │ │ (prompts +  │ │   rules,   │
 │           │ │            │ │  workspace) │ │   skills)  │
 └───────────┘ └────────────┘ └─────────────┘ └────────────┘
```

A [Minion](modules/agent.md) ties it all together: it talks to an LLM through
pydantic-ai (OpenRouter by default), calls [tools](modules/tools.md) you define
or load from [MCP](modules/agent.md) servers, reads and writes
[memory](modules/memory.md), and injects [workspace](modules/workspaces.md)
[context](modules/context.md) into every prompt.

<div class="home-cta" markdown>

## Ready to build something amazing?

Join the developers building the future of autonomous AI.

[Get Started](getting-started.md){ .md-button .md-button--primary }
[Read the Docs](modules/agent.md){ .md-button }

</div>
