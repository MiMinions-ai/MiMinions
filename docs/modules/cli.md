# CLI & Chat

The `miminions` console command is the primary surface for the framework: it manages agents, tasks, knowledge, workspaces, and execution sessions, and it hosts the interactive **chat** and one-shot **prompt** runtimes that drive a live [Minion](agent.md).

```bash
# Installed as a console script…
miminions --help

# …or run as a module
python -m miminions --help
```

!!! info "State lives under `~/.miminions/`"
    All persistent CLI state is stored as JSON under your home directory: `config.json`, `auth.json`, `agents.json`, `tasks.json`, `knowledge.json`, `sessions.json`, `interactions.json`, plus a `workspaces/` tree. On the **first** invocation of any command, MiMinions bootstraps a **`default` workspace** and a **`default` agent** so the chat/prompt commands work out of the box.

```bash
# Explicitly initialize (or verify) default bootstrap state
miminions init

# Repair bootstrap state and restore missing default templates
miminions init --force
```

`init` is an explicit, user-facing bootstrap/repair command over the same default setup logic used on first command run. The `--force` option re-runs bootstrap repair so missing default workspace template files are recreated without overwriting existing customized files.

!!! warning "Authentication gating is provisional"
    A `require_auth` decorator wraps the commands in `agent`, `task`, `knowledge`, `workspace`, and `execution`, but auth is **not actively enforced today** — treat the gating as **planned**, the same as the `workflow` group below. The hooks exist in the code so the behavior can be turned on later, but don't rely on commands being blocked when signed out. The `chat` and `prompt` commands are not wrapped at all.

## Command groups at a glance

<div class="grid cards" markdown>

-   :material-login: **`auth`** — local sign-in, status, and config
-   :material-cog-outline: **`config`** — get/set top-level CLI defaults (`default_workspace`, `default_agent`)
-   :material-database-export-outline: **`export`/`import`** — backup and restore agents/tasks/knowledge JSON data
-   :material-robot: **`agent`** — manage agent records, run them, inspect tools
-   :material-message-text: **`chat`** — interactive conversation with memory distillation
-   :material-flash: **`prompt`** — one-shot prompt to the runtime
-   :material-checkbox-marked-circle-outline: **`task`** — track tasks with priority and status
-   :material-book-open-variant: **`knowledge`** — versioned knowledge entries
-   :material-graph-outline: **`workspace`** — workspaces, rules, and on-disk scaffolding
-   :material-play-circle: **`execution`** — live tool-execution sessions and interaction traces
-   :material-lan: **`gateway`** — local gateway runtime, cron jobs, and gateway sessions

</div>

!!! warning "`workflow` is not yet enabled"
    A `workflow` command group exists in the code but is **commented out of the CLI registration** ("not yet implemented"). `miminions workflow ...` will not run today — treat it as **planned**. The workflow tracing *models* are, however, used internally by `execution` (see below) and by the [Tasks & Workflows](tasks.md) module.

---

## `chat`

An interactive, async conversation with a live Minion bound to a workspace.

```bash
# Start a chat in the default workspace
miminions chat start

# Pick a workspace by id or name
miminions chat start --workspace my-project

# Resume a prior conversation by session id
miminions chat start --session 20260621T101500000000Z_a1b2c3d4
```

| Option | Description |
| --- | --- |
| `--workspace <id\|name>` | Workspace to run in. Defaults to the configured default workspace. |
| `--session <id>` | Resume an existing session id (loads prior history into the LLM context). |

Inside the loop, type a message and press Enter to get a reply. Type **`/exit`** or **`/quit`** (or send EOF / `Ctrl-C`) to end the session. Every turn is appended to the session transcript, and on exit a background memory distillation pass runs.

```text
Workspace : my-project
Session   : 20260621T101500000000Z_a1b2c3d4
Model     : openai/gpt-oss-20b:free via OpenRouter
Type '/exit' or '/quit' to end the session.

> summarize the project goals
...
> /exit
Session ended.
```

!!! tip "Needs an LLM backend"
    Chat (and `prompt`) call the live model. With the default OpenRouter provider you must export `OPENROUTER_API_KEY`; otherwise the model call fails and the reply is returned as an `[error] ...` line. See [Agent](agent.md#model-provider-selection) for switching providers.

??? note "Session resumption (how it works)"
    Passing `--session <id>` loads the append-only `.jsonl` transcript from `JsonlSessionStore` and converts it back into native pydantic-ai messages via `load_as_pydantic_messages()`, giving the LLM full conversational context from prior runs. New sessions get an id of the form `YYYYMMDDTHHMMSSffffffZ_<8-char-uuid>`. Transcripts live under `<workspace_root>/sessions/`.

??? note "Background distillation (how it works)"
    When the chat loop ends, a `MemoryDistiller` runs in the `finally` block over the session transcript. It promotes extracted memory across three tiers — Tier 1 → `HISTORY.md`, Tier 2 → `MEMORY.md` "Project Facts", Tier 3 → the global SQLite insight DB at `~/.miminions/global_memory.db`. If a real model is available it uses `create_llm_filter(model)` to extract facts; otherwise it runs the pipeline with an empty placeholder filter. Distillation failures are caught and reported as a warning rather than crashing your terminal. See [Memory](memory.md) for the full pipeline.

---

## `prompt`

A one-shot prompt to the Minion runtime — no interactive loop. The prompt text is a positional argument.

```bash
# Ask once in the default workspace
miminions prompt ask "Summarize the latest changes"

# Target a specific workspace and session
miminions prompt ask "Draft a release note" --workspace my-project --session my-session
```

| Argument / Option | Description |
| --- | --- |
| `PROMPT...` | The prompt (one or more words, joined). Required. |
| `--workspace <id\|name>` | Workspace id or name. Default: `default`. |
| `--session <id>` | Optional existing session id; a new one is created if omitted. |

The command builds a workspace context string via [`ContextBuilder`](context.md), records both the user prompt and assistant reply to the session transcript, and prints the reply. If the workspace does not exist it is created and its files are initialized.

---

## `auth`

Local authentication and configuration.

!!! quote "Local stub, not a remote server"
    `auth signin` does **not** contact any remote service. It validates a username/password locally and writes an `auth.json` marker that the `require_auth` gate checks. There is no account system behind it.

```bash
miminions auth signin --username alice         # prompts for password
miminions auth status
miminions auth signout

# Configure public access and timeout
miminions auth config --public-access true
miminions auth config --auth-timeout 60
miminions auth config                          # show current config
```

| Command | Options | Description |
| --- | --- | --- |
| `signin` | `--username`, `--password`, `--timeout` | Sign in locally (prompts for any missing credential). Writes `auth.json`. |
| `signout` | — | Clear the local auth marker. |
| `status` | — | Show signed-in user and whether public access is enabled. |
| `config` | `--public-access <bool>`, `--auth-timeout <int>` | Read or set config; with no options, prints current settings. Timeout must be ≥ 5 seconds. |

!!! tip "Public access bypasses the gate"
    `miminions auth config --public-access true` lets gated commands run without signing in (they print a "Public access mode." warning). Useful for local development.

---

## `config`

Top-level configuration access for defaults used by CLI commands.

```bash
# Read one key
miminions config get default_workspace
miminions config get default_agent

# Set one key (workspace resolves id/prefix/name to canonical id)
miminions config set default_workspace my-project

# Set default agent (must already exist in agents.json)
miminions config set default_agent researcher
```

| Command | Description |
| --- | --- |
| `get <key>` | Print one value from `config.json`. |
| `set <key> <value>` | Validate and update one value in `config.json`. |

Supported keys:

- `default_workspace`
- `default_agent`

!!! note "`auth config` vs `config`"
    `miminions auth config` manages authentication flags (`public_access`, `auth_timeout`). `miminions config` manages top-level default routing (`default_workspace`, `default_agent`).

---

## `export` / `import`

Backup and restore CLI record stores for cross-machine migration.

```bash
# Export agents/tasks/knowledge to one backup file
miminions export --output ./miminions-backup.json

# Import and merge with existing records
miminions import --input ./miminions-backup.json --mode merge

# Import and replace existing records
miminions import --input ./miminions-backup.json --mode replace
```

| Command | Options | Description |
| --- | --- | --- |
| `export` | `--output <path>` | Export `agents.json`, `tasks.json`, and `knowledge.json` into one backup JSON file. |
| `import` | `--input <path>`, `--mode merge\|replace` | Restore backup data into `agents.json`, `tasks.json`, and `knowledge.json`. |

`--mode merge` keeps existing records and overlays imported ids.
`--mode replace` replaces each target store with imported data.

---

## `agent`

Manage persisted agent records and drive a live Minion built from them. Agent records are CLI extensions of the core [Minion](agent.md) runtime, pre-loaded with a small default toolset (`cli_echo`, `cli_add`, `cli_now_utc`).

All commands that take an agent id accept it as an optional positional argument. When omitted, the `default_agent` from `~/.miminions/config.json` is used.

```bash
miminions agent list
miminions agent show researcher
miminions agent add --name "Researcher" --description "Finds things" --type assistant
miminions agent update researcher --description "Updated"
miminions agent set-goal researcher --goal "Summarize today's notes"
miminions agent run researcher
miminions agent run                            # uses default_agent
miminions agent ask researcher --prompt "what time is it in UTC?"
miminions agent ask --prompt "what time is it in UTC?"  # uses default_agent
miminions agent remove researcher
```

### Records & lifecycle

| Command | Options | Description |
| --- | --- | --- |
| `list` | `--json` | List all agent records with status and description. |
| `show <ref>` | `--json` | Show full details for one agent by id, id prefix, or exact name. |
| `add` | `--name`, `--description`, `--type` | Create a record (id is the slugified name). All three are prompted if omitted. |
| `update <id>` | `--name`, `--description`, `--type` | Update fields on an existing record. |
| `remove <id>` | — | Delete a record (asks for confirmation). |
| `set-goal [id]` | `--goal` | Store a goal used by `run`. `id` defaults to `default_agent`. |
| `run [id]` | `--async` | Build the runtime and execute the stored goal. `id` defaults to `default_agent`. Requires a goal to be set. |
| `ask [id]` | `--prompt` | One-off prompt to the agent without mutating its stored goal. `id` defaults to `default_agent`. |

`show <ref>` accepts an exact id, an id prefix, or an exact agent name.

!!! warning "`run --async` is not functional"
    The `--async` flag on `agent run` currently prints a `TODO` placeholder and does **not** execute anything asynchronously. Use plain `miminions agent run [id]` for real execution.

### Inspecting and running tools

These commands build the agent's runtime and operate on its registered tools.

| Command | Arguments / Options | Description |
| --- | --- | --- |
| `tool-list [id]` | — | List the agent's tool names and descriptions. `id` defaults to `default_agent`. |
| `tool-info [id] <tool>` | — | Show a tool's description and JSON parameter schema. `id` defaults to `default_agent`. |
| `tool-search [id] <query>` | — | Search tools by name/description (substring). `id` defaults to `default_agent`. |
| `tool-run [id] <tool>` | `--arguments '<json>'` | Execute one tool with a JSON-object argument map and print the structured result (status, result/error, timing). `id` defaults to `default_agent`. |

```bash
miminions agent tool-list researcher
miminions agent tool-list                            # uses default_agent
miminions agent tool-run researcher cli_add --arguments '{"a": 2, "b": 3}'
miminions agent tool-run cli_add --arguments '{"a": 2, "b": 3}'  # uses default_agent
```

---

## `task`

Track tasks with priority, status, and an optional assigned agent. Records persist to `tasks.json`.

```bash
miminions task list
miminions task add --title "Write docs" --description "CLI page" --priority high
miminions task update <id> --status in_progress --agent researcher
miminions task duplicate <id> --title "Write docs (v2)"
miminions task show <id>
miminions task remove <id>
```

| Command | Options | Description |
| --- | --- | --- |
| `list` | `--json` | List all tasks with status and priority. |
| `add` | `--title`, `--description`, `--priority`, `--agent` | Create a task. |
| `update <id>` | `--title`, `--description`, `--priority`, `--status`, `--agent` | Update one or more fields. |
| `duplicate <id>` | `--title` | Copy a task (reset to `pending`). |
| `show <id>` | `--json` | Print full task detail. |
| `remove <id>` | — | Delete a task (asks for confirmation). |

- `--priority` is one of `low`, `medium` (default), `high`.
- `--status` is one of `pending`, `in_progress`, `completed`, `cancelled`.

!!! note "CLI tasks vs. the task runtime"
    These commands manage lightweight *task records* in JSON. They are distinct from the programmatic concurrent [`TaskRuntime`](tasks.md) (which runs agent-bound tasks via `asyncio.TaskGroup`).

---

## `knowledge`

Versioned knowledge entries persisted to `knowledge.json`. Each content change records a new version.

```bash
miminions knowledge list
miminions knowledge add --title "Deploy Steps" --content "..." --category ops --tags "deploy,ci"
miminions knowledge update <id> --content "revised steps"
miminions knowledge version <id>
miminions knowledge revert <id> --version 1.0
miminions knowledge show <id>
miminions knowledge remove <id>
```

| Command | Options | Description |
| --- | --- | --- |
| `list` | `--json` | List entries with version, category, and status. |
| `add` | `--title`, `--content`, `--category`, `--tags` | Create an entry at version `1.0`. |
| `update <id>` | `--title`, `--content`, `--category`, `--tags` | Update fields; a content change bumps the version. |
| `revert <id>` | `--version` | Restore content from a recorded version. |
| `version <id>` | — | Show the version history. |
| `customize <id>` | `--template`, `--format` | Apply a template and/or render as `json` / `markdown` / `plain`. |
| `show <id>` | `--json` | Print full entry detail. |
| `remove <id>` | — | Delete an entry (asks for confirmation). |

!!! tip "Version bumps"
    Updating `--content` to a new value appends a snapshot and increments the version by **+0.1** (e.g. `1.0 → 1.1`). Use `revert --version <v>` to roll back to any recorded snapshot.

---

## `workspace`

Manage workspaces — the in-memory/on-disk model of [nodes and rules](workspaces.md) plus the on-disk `prompt/ memory/ skills/ sessions/ data/` scaffolding.

```bash
miminions workspace list
miminions workspace add --name "My Project" --description "Demo"
miminions workspace add --name "Demo" --sample --init-files
miminions workspace show <id|name>
miminions workspace update <id> --name "Renamed"
miminions workspace set-state <id> --key priority --value high
miminions workspace remove <id>
```

Workspace references accept either a full id, an id **prefix**, or the workspace **name**.

### Workspace lifecycle

| Command | Options | Description |
| --- | --- | --- |
| `list` | `--json` | List workspaces with node/rule counts. |
| `add` | `--name`, `--description`, `--sample`, `--init-files`, `--root-path` | Create a workspace. `--sample` seeds example nodes/rules; `--init-files` scaffolds the on-disk folder; `--root-path` overrides where files are written. |
| `show <ref>` | `--json` | Print full workspace detail (nodes, rules, inherited rules, state). |
| `update <ref>` | `--name`, `--description` | Rename or re-describe. |
| `remove <ref>` | `--force` | Delete a workspace (confirm unless `--force`). |
| `set-state <ref>` | `--key`, `--value` | Set a state value (value is parsed as JSON when possible). |
| `init-files <ref>` | `--path` | Scaffold prompt/memory/skills/sessions/data files for an existing workspace. |

### Rules

| Command | Options | Description |
| --- | --- | --- |
| `add-rule <ref>` | `--name`, `--description`, `--priority`, `--enabled/--disabled`, `--condition`, `--action` | Add a rule. `--priority` is `LOW`/`MEDIUM`/`HIGH`/`CRITICAL`. `--condition`/`--action` take a JSON object (or a bare string treated as `{"type": "<value>"}`). |
| `remove-rule <ref> <rule>` | — | Remove a rule by id, id prefix, or name. |

```bash
miminions workspace add-rule my-project \
  --name "escalate" --priority HIGH \
  --condition '{"type":"state_equals","key":"priority","value":"high"}' \
  --action '{"type":"assign_task","message":"escalate now"}'
```

---

## `execution`

A live tool-execution runtime: start a session, register tool modules, run individual tools, and review the recorded interactions. Each tool run is captured as a `WorkflowRun` trace and persisted to `interactions.json` (the same schema used by the [workflow tracing layer](tasks.md)).

```bash
# 1. Start a session
miminions execution session start --name demo

# 2. Register a Python module that defines GenericTool instances
miminions execution add-tool ./my_tools.py

# 3. Run a tool with KEY=VALUE inputs
miminions execution run my_tool --input city=Tokyo --input units=metric

# 4. Review what happened
miminions execution interaction list
miminions execution interaction show 0

# 5. Stop the session
miminions execution session stop
```

### Sessions

| Command | Options | Description |
| --- | --- | --- |
| `session start` | `--name` | Start a new session (only one active at a time). |
| `session stop` | — | Stop the active session. |
| `session list` | `--json` | List all sessions with status. |

### Tools & runs

| Command | Arguments / Options | Description |
| --- | --- | --- |
| `add-tool <path.py>` | — | Load `GenericTool` instances from a `.py` file into the active session. |
| `run <tool>` | `--input KEY=VALUE` (repeatable) | Execute a registered tool with string inputs; prints result/error and records a `WorkflowRun`. |
| `test` | `--prompt` | Run every registered tool with its default parameters and record the batch as one `WorkflowRun`. |

### Interactions

| Command | Arguments / Options | Description |
| --- | --- | --- |
| `interaction list` | `--session-id`, `--json` | List recorded `WorkflowRun`s for a session (defaults to the active one). |
| `interaction show <index>` | `--session-id`, `--json` | Print the full JSON of a recorded `WorkflowRun`. |

!!! note "Tool modules"
    `add-tool` imports any module-level objects that are `GenericTool` instances. Define your tools with `@tool(...)` or `create_tool(...)` from `miminions.tools` (see [Tools](tools.md)) and point `add-tool` at the file.

---

## `gateway`

Manage the local gateway runtime for a workspace, plus gateway cron jobs and gateway-specific sessions. The command group is registered, but it still exposes local runtime controls rather than hosted channel integrations.

```bash
miminions gateway status --workspace Demo
miminions gateway run --workspace Demo
miminions gateway cron list --workspace Demo
miminions gateway sessions list --workspace Demo
```

| Command | Options | Description |
| --- | --- | --- |
| `status` | `--workspace` | Show workspace gateway paths, session count, and cron job count. |
| `run` | `--workspace`, `--no-cron`, `--log-level` | Start the local gateway runtime until interrupted. |
| `cron list` | `--workspace`, `--all` | List gateway cron jobs. |
| `cron add-every` | `--workspace`, `--name`, interval option, `--message` | Add a recurring interval job. |
| `cron add-at` | `--workspace`, `--name`, `--at`, `--message` | Add a one-shot ISO-datetime job. |
| `cron add-cron` | `--workspace`, `--name`, `--expr`, `--tz`, `--message` | Add a cron-expression job; requires `croniter`. |
| `cron remove` / `enable` / `disable` / `run` | `--workspace` plus job id | Manage or trigger an existing cron job. |
| `sessions list` / `show` / `delete` | `--workspace` plus session options | Inspect or delete gateway sessions. |

!!! note "Workspace root required"
    Gateway commands resolve an existing workspace and require it to have a `root_path`. Run `miminions workspace init-files <workspace>` first if needed.

---

## Where things live

| Path | Contents |
| --- | --- |
| `~/.miminions/config.json` | CLI config + default workspace/agent ids |
| `~/.miminions/auth.json` | Local sign-in marker |
| `~/.miminions/agents.json` · `tasks.json` · `knowledge.json` | Record stores for the respective groups |
| `~/.miminions/sessions.json` · `interactions.json` | `execution` sessions and recorded traces |
| `~/.miminions/workspaces/` | Per-workspace on-disk folders (`prompt/ memory/ skills/ sessions/ data/`) |
| `~/.miminions/global_memory.db` | Tier-3 global SQLite insight store (written by chat distillation) |

## Related

- [Agent](agent.md) — the `Minion` runtime the CLI drives
- [Workspaces](workspaces.md) — nodes, rules, and on-disk layout
- [Memory](memory.md) — the three-tier memory and distillation pipeline
- [Tasks & Workflows](tasks.md) — the programmatic task runtime and workflow traces
