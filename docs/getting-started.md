# Getting Started

This guide walks you from a clean environment to a working agent, then through the
`miminions` CLI and a development setup. Every snippet runs against the real API.

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

## Using the CLI

Installing the package registers a `miminions` console command (you can also run
`python -m miminions`). On first run it bootstraps a `default` workspace and a
default agent under `~/.miminions/`, where all CLI state persists (set
`MIMINIONS_HOME` to relocate it).

```bash
miminions --help
```

Registered command groups: `auth`, `agent`, `tool`, `task`, `knowledge`, `workspace`,
`execution`, `chat`, `gateway`, `prompt`.

### Chat

Start an interactive async chat session. It runs against the default workspace
unless you pass `--workspace`, and each reply streams to the terminal as it is
generated.

```bash
# Interactive session against the default workspace
miminions chat start

# Use a specific workspace (id or name)
miminions chat start --workspace "Demo"

# Resume a prior session — its history is reloaded into LLM context
miminions chat start --session <session_id>

# Show tool calls and per-turn token usage / latency
miminions chat start --verbose
```

Type `/exit` or `/quit` to end the session.

### One-shot prompt

Send a single prompt and print the reply (no interactive loop). Workspace
context is injected automatically via [`ContextBuilder`](modules/context.md).

```bash
miminions prompt ask "Summarize the project facts in this workspace"

# Target a workspace and/or session explicitly
miminions prompt ask --workspace "Demo" "What rules are active here?"
```

### Common Use Cases

#### 1. Writing and editing content

**Fit:** Strong

Use `prompt ask` for one-off drafts and `chat start` for iterative editing.

    # One-off draft
    miminions prompt ask "Draft a launch update for our weekly team newsletter."

    # Iterative editing session
    miminions chat start

#### 2. Coding support

**Fit:** Strong

Use chat/prompt for code generation, bug explanation, and refactor suggestions.
Optionally create a coding-focused agent for a reusable setup.

    # Ask for code help directly
    miminions prompt ask "Explain this stack trace and suggest a fix strategy."

    # Interactive coding loop
    miminions chat start

    # Optional: create a dedicated coding agent
    miminions agent add

#### 3. Research and summarization

**Fit:** Strong

Use chat/prompt to summarize text, compare options, and extract key points.

    miminions prompt ask "Summarize the key tradeoffs between option A and option B."
    miminions chat start

#### 4. Customer support automation

**Fit:** Partial

MiMinions is strong for drafting replies and FAQ content. Full ticket routing
and automation typically needs extra workflow/tool integration.

    # Draft support replies or FAQ content
    miminions prompt ask "Draft a friendly reply for a delayed order complaint."

    # Add workflow/tool integration for deeper automation
    miminions execution --help

#### 5. Personal productivity

**Fit:** Strong

Use `task` commands for planning/prioritization, `knowledge` for notes, and
`chat` for ongoing planning.

    miminions task --help
    miminions knowledge --help
    miminions chat start

#### 6. Data analysis help

**Fit:** Partial to strong

MiMinions is strong for explanation, query drafting, and insight summaries.
Deeper automated analysis depends on connecting data/tools through execution.

    # Ask for analysis framing or query drafting
    miminions prompt ask "Draft SQL to compare weekly active users month over month."

    # Extend with custom tooling/data integration
    miminions execution --help

### Agents

```bash
# List persisted CLI agents
miminions agent list

# Add an agent (prompts for name/description/type)
miminions agent add

# Give it a goal, then run it
miminions agent set-goal default --goal "Add 2 and 3"
miminions agent run default

# Inspect an agent's tools
miminions tool list default
miminions agent ask default --prompt "echo hello"
```

!!! note
    On `agent run`, the `--async` flag is **not yet functional** — it just prints a
    placeholder. Run agents synchronously for now.

### Workspaces

```bash
# List all workspaces
miminions workspace list

# Create a workspace populated with example nodes and rules
miminions workspace add --name "Demo" --description "Demo workspace" --sample

# Create a workspace and scaffold its prompt/memory/skills/sessions/data files
miminions workspace add --name "Demo2" --init-files

# Show details for one workspace (by id prefix or name)
miminions workspace show Demo

# Update, set state, manage rules
miminions workspace update Demo --description "Updated description"
miminions workspace set-state Demo --key phase --value "review"
miminions workspace add-rule Demo --name "gate" --priority HIGH \
    --condition '{"type":"state_equals","key":"phase","value":"review"}'
miminions workspace remove-rule Demo gate

# Scaffold files for an existing workspace
miminions workspace init-files Demo

# Remove a workspace
miminions workspace remove Demo
```

The full workspace subcommand set is
`list` / `add` / `show` / `update` / `remove` / `set-state` / `add-rule` /
`remove-rule` / `init-files`. See [Workspaces](modules/workspaces.md) for the
underlying model and the [CLI reference](modules/cli.md) for every command group.

## Development Setup

```bash
git clone https://github.com/MiMinions-ai/MiMinions.git
cd MiMinions
pip install -e ".[dev]"
pytest tests/
```

The `[dev]` extra pulls in `pytest`, `pytest-asyncio`, `pytest-cov`, `flake8`,
and `build`. Async tests run automatically (`asyncio_mode = "auto"`).

### Running tests by layer

```bash
pytest tests/unit/          # fast, isolated unit tests
pytest tests/integration/   # integration tests
pytest tests/e2e/           # end-to-end tests
```

All three layers run under `pytest`; there is no separate runner script.

## Publishing

Build and publish the distribution with `uv`:

```bash
uv build
uv publish
```

Build a standalone CLI binary with [PyInstaller](https://pyinstaller.org/)
(install the `[cli-build]` extra first):

```bash
pip install miminions[cli-build]
bash deploy/build_cli.sh
```

---

Ready to go deeper? Explore the module guides:
[Agent](modules/agent.md) ·
[Memory](modules/memory.md) ·
[Context](modules/context.md) ·
[Tools](modules/tools.md) ·
[Workspaces](modules/workspaces.md) ·
[Tasks](modules/tasks.md) ·
[Data](modules/data.md) ·
[Gateway](modules/gateway.md) ·
[CLI](modules/cli.md).

## Practice use cases

- [Real-estate deal desk](use-cases/real-estate-deal-desk.md) — underwrite tool + three-tier memory starter
