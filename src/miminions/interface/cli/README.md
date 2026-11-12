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
| `agent.py` | `miminions agent` | Manage and run agents; per-agent memory (`memory-attach/store/recall/update/delete`, `ingest-document`) |
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
miminions chat start --project ./my-project
miminions chat start --no-discovery # use the configured workspace
```

Chat and `prompt ask` detect Python projects in the current directory. An explicit
`--workspace` wins over detection; `--project PATH` selects a directory and cannot
be combined with `--workspace` or `--no-discovery`. Each project has a stable
workspace association based on its canonical path. State, sessions, memory, and
the rebuildable discovery cache stay under `MIMINIONS_HOME`, outside the project.
Moving a project creates a new association; existing workspace records need no migration.

Discovery reads ASTs without importing code. Chat shows local capabilities before
any model request. The agent uses `workspace_search_tools` to activate relevant
functions; every invocation then requires a separate approval, including import
side effects. Detached/noninteractive tasks wait for `miminions task approve`.

Each task loads provider API credentials from the selected project's `.env`, or
from the launch directory's `.env` for nonproject workflows. Nonempty exported
keys take precedence. Only provider keys are loaded; they never enter persisted
task requests, the supervisor, or transcripts. Files are reread each turn and for
distillation, allowing key changes without a supervisor restart.

- **Session resumption** — `--session <id>` loads the `.jsonl` transcript from
  `JsonlSessionStore` (under `<workspace_root>/sessions/`) and replays it as
  native `pydantic_ai` messages, restoring full conversational context.
- **Background distillation** — typing `/exit` or `/quit` ends the session and
  runs `MemoryDistiller` to extract facts into the workspace's memory.

## Contract

> [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md) — Contract v3 (project-aware chat/prompt options; additive).
> **Public surface:** `cli` with 13 lazy groups (`auth agent tool task instance knowledge workspace chat gateway prompt config export import`) plus the standalone `init` bootstrap command (eagerly registered) — 14 top-level entry points; root `--help` must stay lazy/cheap.
> **State:** `~/.miminions/` (override `MIMINIONS_HOME`); default workspace/agent bootstrapped on first real subcommand only.
> **Lifecycle:** lazy import per group; `workflow.py`/`execution.py`/`dispatch.py`/`persistence.py` stay internal (no shipped group).
> **Gate:** `tests/integration/cli/` + `scripts/check_structure.py` (asserts this list matches `cli/main.py`).'s memory.
