# Context Builder

The `context` package contains the `ContextBuilder` which is responsible for dynamically assembling the agent's system prompt from the workspace state.

## Core Responsibilities

- Reads prompt files from `prompt/` (e.g. `AGENTS.md`, `USER.md`).
- Reads the workspace state and injects it into the prompt.
- Queries `SQLiteMemory` (Tier 3) to inject cross-workspace insights (`## Global Knowledge`).
- Reads local markdown memory (`memory/MEMORY.md`, Tier 2) and injects it.
- Dynamically generates the complete, fully-resolved system prompt right before the LLM call.
