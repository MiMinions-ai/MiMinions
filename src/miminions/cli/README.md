# MiMinions CLI

The `miminions.cli` package is the Click-based command-line interface. The entry
point is `cli/main.py` (exposed as the `miminions` console command and via
`python -m miminions`). State persists locally under `~/.miminions/`, and a
default workspace + agent are bootstrapped on first run.

> Full reference: [CLI & Chat documentation](https://miminions.ai/modules/cli/).

## Command groups

| Module | Command | Purpose |
|--------|---------|---------|
| `auth.py` | `miminions auth` | Local sign-in, public-access mode, config |
| `agent.py` | `miminions agent` | Manage and run agents |
| `tool.py` | `miminions tool` | Discover, execute, and trace agent tools and tool sessions |
| `chat.py` | `miminions chat` | Interactive async chat loop |
| `prompt.py` | `miminions prompt` | One-shot prompt to a workspace agent |
| `task.py` | `miminions task` | Task CRUD |
| `knowledge.py` | `miminions knowledge` | Versioned knowledge base |
| `workspace.py` | `miminions workspace` | Workspaces, nodes, rules, on-disk files |
| `execution.py` | internal | Tool-session persistence, execution, and recorded history |
| `gateway.py` | `miminions gateway` | Local gateway runtime, cron jobs, and sessions |

## Chat

```bash
miminions chat start                 # new session in the default workspace
miminions chat start --session <id>  # resume a prior session
```

- **Session resumption** — `--session <id>` loads the `.jsonl` transcript from
  `JsonlSessionStore` (under `<workspace_root>/sessions/`) and replays it as
  native `pydantic_ai` messages, restoring full conversational context.
- **Background distillation** — typing `/exit` or `/quit` ends the session and
  runs `MemoryDistiller` to extract facts into the workspace's memory.

## Contract

> [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md) — Contract v1.
> **Public surface:** `cli` with 13 lazy groups (`auth agent tool task instance knowledge workspace chat gateway prompt config export import`); root `--help` must stay lazy/cheap.
> **State:** `~/.miminions/` (override `MIMINIONS_HOME`); default workspace/agent bootstrapped on first real subcommand only.
> **Lifecycle:** lazy import per group; `workflow.py`/`execution.py`/`dispatch.py`/`persistence.py` stay internal (no shipped group).
> **Gate:** `tests/integration/cli/` + `scripts/check_structure.py` (asserts this list matches `cli/main.py`).'s memory.
