# Context Builder

The `context` package contains the `ContextBuilder`, which dynamically assembles
the agent's system prompt from workspace state and stored memory.

> Full reference: [Context Builder documentation](https://miminions.ai/modules/context/).

## Core Responsibilities

- Reads the bootstrap prompt files from `prompt/` (`AGENTS.md`, `USER.md`, `TOOLS.md`, `IDENTITY.md`).
- Summarizes the workspace graph (nodes, rules, state) into the prompt.
- Optionally queries the global SQLite vector store (Tier 3) for cross-workspace insights (`## Global Knowledge`).
- Reads local markdown memory (`memory/MEMORY.md`, Tier 2) and injects it.
- Lists available skills from `skills/<name>/SKILL.md`.
- Returns the complete, fully-resolved system prompt as a string.

## Usage

`ContextBuilder` is wired into the agent via `Minion.set_context(workspace, root_path)`
and runs on every `run()` call. To build a prompt directly:

```python
from miminions.context import ContextBuilder

system_prompt = ContextBuilder(global_top_k=5).build(workspace, root_path)
```

Note the call shape: `build()` takes the workspace and root path as arguments.
