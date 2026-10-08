# Getting Started

This guide walks you from a clean environment to a working agent, then 
a development setup. Every snippet runs against the real API.

## Installation

=== "pip"

    ```bash
    # Core framework
    pip install miminions

    # Core + SQLite vector memory (fastembed + sqlite-vec + pysqlite3)
    pip install miminions[sqlite]

    # Everything (same extras as [sqlite])
    pip install miminions[all]
    ```

=== "uv"

    ```bash
    uv add miminions
    # with vector memory:
    uv add "miminions[sqlite]"
    ```

!!! note "What's in core vs. `[sqlite]`"
    The **core** install gives you the agent runtime (`pydantic_ai`-backed),
    the tools system, workspaces, the markdown memory store, the data store, and
    the full CLI. It does **not** bundle `fastembed` or `sqlite-vec`.

    The **`[sqlite]`** extra adds [`SQLiteMemory`](modules/memory.md) — a local
    vector store that embeds text with `fastembed` and runs KNN search through
    `sqlite-vec`. Install it if you want semantic recall or the three-tier global
    memory. The first time you construct `SQLiteMemory`, the embedding model is
    downloaded.

## Requirements

- **Python 3.12+** (the package declares `requires-python = ">=3.12"`).
- An LLM backend. By default MiMinions talks to [OpenRouter](https://openrouter.ai/),
  so set an API key:

  ```bash
  export OPENROUTER_API_KEY="sk-or-..."
  ```

  The default model is the free `openai/gpt-oss-20b:free`. You can pick a
  different provider or model instead — see
  [Choosing a model / provider](#choosing-a-model-provider) below. For offline
  experiments, `provider="test"` needs no key at all.

## Architecture

```text
┌─────────────────────────────────────────────────────────────┐
│                       CLI / Chat                            │
└─────────────────────────┬───────────────────────────────────┘
                          │
┌─────────────────────────▼───────────────────────────────────┐
│                      Minion Agent                           │
│              (OpenRouter + MCP servers)                     │
└──────┬──────────────┬──────────────┬──────────────┬─────────┘
       │              │              │              │
 ┌─────▼─────┐ ┌──────▼─────┐ ┌──────▼──────┐ ┌─────▼──────┐
 │   Tools   │ │   Memory   │ │   Context   │ │ Workspaces │
 │ (Generic, │ │ (MD files  │ │   Builder   │ │  (nodes,   │
 │   MCP)    │ │ + SQLite)  │ │ (prompts +  │ │   rules,   │
 │           │ │            │ │  workspace) │ │   skills)  │
 └───────────┘ └────────────┘ └─────────────┘ └────────────┘
```

A [Minion](modules/agent.md) ties it all together: it talks to an LLM 
(OpenRouter by default), calls [tools](modules/tools.md) you define
or load from [MCP](modules/agent.md) servers, reads and writes
[memory](modules/memory.md), and injects [workspace](modules/workspaces.md)
[context](modules/context.md) into every prompt.


## Your First Agent

Create a [`Minion`](modules/agent.md), register a plain Python function as a tool,
and `await run(...)`. Tool schemas are inferred from the function signature.

```python
import asyncio
from miminions.agent import create_minion


async def main():
    agent = create_minion("MyAgent", description="A small demo agent")

    def calculator(operation: str, a: int, b: int) -> int:
        """Perform a basic arithmetic operation."""
        if operation == "add":
            return a + b
        if operation == "multiply":
            return a * b
        return 0

    agent.register_tool("calculator", "Perform arithmetic", calculator)

    reply = await agent.run("What is 6 multiplied by 7?")
    print(reply)


asyncio.run(main())
```

!!! tip "Import from subpackages, never the top level"
    `import miminions` exposes nothing — `from miminions import Minion` will fail.
    Always import from the subpackage, e.g. `from miminions.agent import create_minion`,
    `from miminions.tools import GenericTool`, `from miminions.data import LocalDataManager`.

### Choosing a model / provider

`create_minion(provider=...)` selects an LLM backend through the internal
`ModelFactory`. Supported provider strings:

| Provider      | Default model                  | Key / notes                          |
| ------------- | ------------------------------ | ------------------------------------ |
| `openrouter`  | `openai/gpt-oss-20b:free`      | default; needs `OPENROUTER_API_KEY`  |
| `openai`      | `gpt-4o`                       | needs an OpenAI key in the environment |
| `anthropic`   | `claude-3-5-sonnet-latest`     | needs an Anthropic key in the environment |
| `gemini`      | `gemini-1.5-flash`             | needs a Google API key in the environment |
| `test`        | `TestModel` (offline)          | no key; deterministic, great for tests |

```python
# Pick a provider by name:
agent = create_minion("MyAgent", provider="anthropic")

# Offline / no network — ideal for unit tests:
agent = create_minion("MyAgent", provider="test")

# Or pass a fully constructed pydantic_ai model directly:
from pydantic_ai.models.openai import OpenAIModel
agent = create_minion("MyAgent", model=OpenAIModel("gpt-4o"))
```

!!! warning "When missing keys surface"
    With the default `openrouter` provider, a missing `OPENROUTER_API_KEY` fails
    **fast**: `create_minion(...)` raises `ValueError` at construction. The other
    real providers build fine without a key and instead raise an auth/network
    error at `await agent.run(...)` time. Use `provider="test"` to exercise your
    tools and wiring without any credentials.

Next steps from here: attach [Memory](modules/memory.md), wire in
[Workspaces](modules/workspaces.md) and [Context](modules/context.md), or expose
external tools over [MCP](modules/agent.md). See the
[Tools](modules/tools.md) and [Tasks](modules/tasks.md) pages for more.


## Development Setup

```bash
git clone https://github.com/MiMinions-ai/MiMinions.git
cd MiMinions
pip install -e ".[dev]"
pytest tests/
```

The `[dev]` extra pulls in extra utilities to facilitate the tests.

### Running tests by layer

```bash
pytest tests/unit/          # fast, isolated unit tests
pytest tests/integration/   # integration tests
pytest tests/e2e/           # end-to-end tests
```

All three layers run under `pytest`; there is no separate runner script.

---

Ready to go deeper? Explore the module guides:
[Agent](modules/agent.md) ·
[Memory](modules/memory.md) ·
[Context](modules/context.md) ·
[Tools](modules/tools.md) ·
[Workspaces](modules/workspaces.md)

## Practice use cases
- [Single Agent Use Cases](use-cases/single-agent-use-cases.md) - Multiple agents each setup for different use cases.
- [Real-estate deal desk](use-cases/real-estate-deal-desk.md) — underwrite tool + three-tier memory starter
