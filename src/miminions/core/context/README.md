# Context Assembly and Memory Processing

`miminions.core.context` assembles system prompts and implements memory
distillation, budgeting and compaction. These are related but distinct jobs:
prompt assembly reads material for a model request; distillation and compaction
update persistent memory.

> Full reference: [Context Builder documentation](https://miminions.ai/modules/context/).

## Implementation ownership

| Module | Responsibility |
|--------|----------------|
| [context_builder.py](context_builder.py) | Load workspace inputs/global insights and render a system-prompt string. |
| [strategies.py](strategies.py), [dedupe.py](dedupe.py) | Fit prompt sections to budgets and remove duplicated memory text. |
| [distiller.py](distiller.py), [llm_filter.py](llm_filter.py) | Extract summaries/facts from transcripts and coordinate memory promotion. |
| [budget.py](budget.py), [compaction.py](compaction.py) | Measure memory pressure, compact facts and record budget outcomes. |

Memory-processing helpers are also re-exported by
[core.agent.memory](../agent/memory/README.md). Markdown IO is implemented in
[system.file.md_store](../../system/file/md_store.py), vector storage in
[system.db.sqlite](../../system/db/sqlite.py), and transcripts in
[interface.session](../../interface/session.py). Re-exporting a helper does not
move its implementation into the memory package.

## Core Responsibilities

- Reads the bootstrap prompt files from `prompt/` (`AGENTS.md`, `USER.md`, `TOOLS.md`, `IDENTITY.md`).
- Summarizes the workspace graph (nodes, rules, state) into the prompt.
- Optionally queries the global SQLite vector store (Tier 3) for cross-workspace insights (`## Global Knowledge`).
- Reads local markdown memory (`memory/MEMORY.md`, Tier 2) and injects it.
- Lists available skills from `skills/<name>/SKILL.md`.
- Returns the complete, fully-resolved system prompt as a string.

## Usage

`Minion.set_context(workspace, root_path)` attaches the workspace used by the
agent's system-prompt callback. To build a prompt directly:

```python
from miminions.core.context import ContextBuilder

system_prompt = ContextBuilder(global_top_k=5).build(workspace, root_path)
```

`build(..., project_context=None)` accepts optional project discovery metadata.
The project section is bounded to 4,000 tokens and identifies reference text as
untrusted data. Project mode distinguishes the state root from the project root,
explains per-call approval, and guides capability search and task clarification.
Omitting this argument retains the existing data-directory boundary and prompt.

Note the call shape: `build()` takes the workspace and root path as arguments.

## Contract

> [Recursive, Bounded Evolution](../../../../docs/architecture/recursive-evolution.md) — Contract v2 (optional project context; additive).
> **Public surface:** the package root exports `ContextBuilder`; memory-processing APIs are also exposed through `core.agent.memory`.
> **State:** the builder holds strategies/budgets and performs filesystem/database reads; reading Markdown memory can initialize missing files. Distillation/compaction write workspace memory, global SQLite entries and budget state (`memory/BUDGET_STATE.json`). This is not a pure, stateless package.
> **Lifecycle:** prompt assembly reads `prompt/` + `memory/MEMORY.md` + Tier-3 global + `skills/` and returns a string. Separately, distillation promotes extracted facts and compacts over-budget workspace memory.
> **Gate:** context tests (`tests/integration/context/`) + `scripts/check_structure.py`.
