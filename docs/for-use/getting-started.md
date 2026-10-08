# Getting Started

This guide walks you from a clean environment to the `miminions` CLI and a development setup.
Every snippet runs against the real API.

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
    The **core** install gives you the agent runtime,
    the tools system, workspaces, the markdown memory store, the data store, and
    the full CLI. It does **not** bundle `fastembed` or `sqlite-vec`.

    The **`[sqlite]`** extra adds [`SQLiteMemory`](for-dev/modules/memory.md) — a local
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

## Using the CLI

Installing the package registers a `miminions` console command (you can also run
`python -m miminions`). On first run it bootstraps a `default` workspace and a
default agent under `~/.miminions/`, where all CLI state persists (set
`MIMINIONS_HOME` to relocate it).

```bash
miminions --help
```

Registered command groups: `auth`, `agent`, `tool`, `task`, `knowledge`, `workspace`,
`chat`, `gateway`, `prompt`.

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
context is injected automatically via [`ContextBuilder`](for-dev/modules/context.md).

```bash
miminions prompt ask "Summarize the project facts in this workspace"

# Target a workspace and/or session explicitly
miminions prompt ask --workspace "Demo" "What rules are active here?"
```

---

See [CLI reference](for-use/cli.md) for every command group.
See [Use Cases](for-use/use-cases.md) for common cli use cases.
