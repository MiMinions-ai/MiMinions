# MiMinions CLI

The `miminions.interface.cli` package is the Click-based command-line interface. The entry
point is [main.py](main.py) (exposed as the `miminions` console command and via
`python -m miminions`). State persists locally under `~/.miminions/`, and a
default workspace + agent are bootstrapped on first run.

> Full reference: [CLI & Chat documentation](https://miminions.ai/modules/cli/).

## Command groups

| Module | Command | Purpose |
|--------|---------|---------|
| [auth.py](auth.py) | `miminions auth` | Local sign-in and public-access settings; not a mandatory account gate |
| [management/agent.py](management/agent.py) | `miminions agent` | Saved-agent management, runtime construction and memory operations |
| [management/tool.py](management/tool.py) | `miminions tool` | Discover and execute agent tools |
| [management/instance.py](management/instance.py) | `miminions instance` | Start, inspect and stop the durable execution instance |
| [operations/chat.py](operations/chat.py) | `miminions chat` | Interactive chat and distillation submission |
| [operations/prompt.py](operations/prompt.py) | `miminions prompt` | One-shot prompt submission |
| [management/task.py](management/task.py) | `miminions task` | Saved work-item CRUD and durable execution inspection/control |
| [management/knowledge.py](management/knowledge.py) | `miminions knowledge` | Versioned records in `knowledge.json` |
| [management/workspace.py](management/workspace.py) | `miminions workspace` | Workspaces, nodes, rules and workspace files |
| [daemon.py](daemon.py) | `miminions gateway` | Gateway runtime, cron jobs and gateway sessions |
| [../config.py](../config.py) | `miminions config` | Read and validate CLI configuration |
| [transfer/transfer.py](transfer/transfer.py) | `miminions export` / `miminions import` | Transfer saved records |
| [main.py](main.py) | `miminions init` | Explicit first-run setup or repair |

Internal helpers include [management/project.py](management/project.py) for
project selection, [operations/dispatch.py](operations/dispatch.py) for durable
submission/following, [operations/execution.py](operations/execution.py) for tool
sessions and traces, and [management/workflow.py](management/workflow.py) for
workflow helpers. There are no shipped `execution` or `workflow` command groups.
Shared JSON persistence lives in [core/persistence.py](../../core/persistence.py).

The CLI is not yet a thin presentation layer: execution handlers import its
agent-building, project-loading, tool-session and distillation helpers. Treat
those helpers as shared behavior when changing them, even though their names
or locations look CLI-private.

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

- **Session resumption** — `--session <id>` prefers the execution-store checkpoint
  of native model messages, falling back to reconstruction from the JSONL
  transcript under `<workspace_root>/sessions/`. History is trimmed at turn
  boundaries; resumption does not imply unlimited history.
- **Background distillation** — typing `/exit` or `/quit` ends the session and
  queues `MemoryDistiller` after submitted turns to extract memory.

## Contract

> [Recursive, Bounded Evolution](../../../../docs/architecture/recursive-evolution.md) — Contract v3 (project-aware chat/prompt options; additive).
> **Public surface:** `cli` with 13 lazy groups (`auth agent tool task instance knowledge workspace chat gateway prompt config export import`) plus the standalone `init` bootstrap command (eagerly registered) — 14 top-level entry points; root `--help` must stay lazy/cheap.
> **State:** `~/.miminions/` (override `MIMINIONS_HOME`); default workspace/agent bootstrapped on first real subcommand only.
> **Lifecycle:** lazy import per group; internal helpers support commands and execution handlers.
> **Gate:** `tests/unit/interface/`, `tests/integration/cli/` and `scripts/check_structure.py` (checks registered commands against the repository map).
