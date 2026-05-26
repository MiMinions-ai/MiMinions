# Context Builder

The `miminions.context` module assembles the agent's system prompt dynamically from workspace state and stored memory before every LLM call.

## Responsibilities

- Reads prompt templates from `prompt/` (e.g. `AGENTS.md`, `USER.md`)
- Reads workspace state (nodes, rules, key-value state)
- Queries `SQLiteMemory` (Tier 3) for cross-workspace insights → injected as `## Global Knowledge`
- Reads `memory/MEMORY.md` (Tier 2) for workspace-local facts
- Returns a fully-resolved system prompt string

## How It Fits In

`ContextBuilder` is called internally by `Minion.run()` each time a prompt is sent. You do not need to invoke it manually — just attach a workspace via `agent.set_context()`.

```python
agent = create_minion("MyAgent")
agent.set_context(workspace, root_path="./my_workspace")

# ContextBuilder runs automatically on every agent.run() call
reply = await agent.run("What are the active tasks?")
```

## Direct Usage

```python
from miminions.context import ContextBuilder

builder = ContextBuilder(workspace, root_path="./my_workspace")
system_prompt = builder.build()
print(system_prompt)
```

## Prompt Templates

Place markdown files in `<root_path>/prompt/` to inject static context:

| File | Purpose |
|------|---------|
| `AGENTS.md` | Describes agents registered in the workspace |
| `USER.md` | User preferences or persona |

Any `.md` file placed in `prompt/` is automatically included.
