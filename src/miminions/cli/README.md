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
| `tool.py` | `miminions tool` | Discover, inspect, and run agent tools |
| `chat.py` | `miminions chat` | Interactive async chat loop |
| `prompt.py` | `miminions prompt` | One-shot prompt to a workspace agent |
| `task.py` | `miminions task` | Task CRUD |
| `knowledge.py` | `miminions knowledge` | Versioned knowledge base |
| `workspace.py` | `miminions workspace` | Workspaces, nodes, rules, on-disk files |
| `execution.py` | `miminions execution` | Execution sessions and recorded tool runs |
| `gateway.py` | `miminions gateway` | Local gateway runtime, cron jobs, and sessions |

> `workflow.py` exists but is **not registered** in `main.py`
> (`miminions workflow` is currently unreachable). The `--async` flag on
> `miminions agent run` is a no-op placeholder.

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
