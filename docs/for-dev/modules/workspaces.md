# Workspaces

A **workspace** is the named container that gives a [Minion](agent.md) its identity, its
memory, and its boundaries. Every workspace has two halves:

<div class="grid cards" markdown>

-   :material-graph-outline: __In-memory graph__

    A network of typed **Nodes** and prioritized **Rules** (with inheritance) plus a
    free-form `state` dict, persisted as JSON in `workspaces.json`.

-   :material-folder-outline: __On-disk folder__

    A `prompt/ memory/ skills/ sessions/ data/` directory tree that drives the agent's
    system prompt and three-tier [memory](memory.md).

</div>

The graph is the structured model you query and reason about; the folder is what the
[Context Builder](context.md) reads on every turn to assemble the agent's system prompt.

!!! note "Import from the submodules"
    `from miminions import ...` exposes nothing. The graph model lives in
    `miminions.core.workspace`, and the on-disk helpers in `miminions.workspace_fs`.

## Quick Start

```python
from pathlib import Path
from miminions.core.workspace import (
    WorkspaceManager, Node, Rule, NodeType, RulePriority, resolve_workspace,
)

# WorkspaceManager REQUIRES a config directory (a Path) — there is no no-arg form.
manager = WorkspaceManager(Path("~/.miminions").expanduser())

# Create an in-memory workspace (not yet persisted).
ws = manager.create_workspace("research", description="My research workspace")

# Build a small node graph.
agent = Node(name="Assistant", type=NodeType.AGENT)
task = Node(name="Summarize", type=NodeType.TASK)
ws.add_node(agent)
ws.add_node(task)
ws.connect_nodes(agent.id, task.id)

# Add a rule (priority-ordered; see "Rules" below).
ws.add_rule(Rule(name="Has an agent", priority=RulePriority.HIGH,
                 condition={"type": "node_type_exists", "node_type": "agent"},
                 action={"type": "assign_task"}))

# Persist all workspaces to <config_dir>/workspaces.json.
manager.save_workspaces({ws.id: ws})

# Later: load and look one up by id, id-prefix, or exact name.
workspaces = manager.load_workspaces()
same_ws = resolve_workspace(workspaces, "research")
print(same_ws.get_network_summary())
```

!!! warning "Resolving a workspace"
    There is **no** `manager.get_workspace(id)`. Load the dict with
    `load_workspaces()` and resolve a single entry with
    `resolve_workspace(workspaces, ref)`, where `ref` is an exact id, an id prefix,
    or the exact name.

### Persistence & schema versioning

`save_workspaces()` writes `workspaces.json` **atomically** (a temp file swapped
into place), so an interrupted save can't corrupt the store. Each persisted
record is stamped with a `schema_version` field (currently `1`):

- Records **without** a version predate versioning and are treated as v1 — they
  get stamped on the next save.
- Records with a **newer** version than the running code supports are loaded
  best-effort with a logged warning.
- Future breaking changes to the record shape will dispatch on this version in
  a migration step at load time.

If `workspaces.json` is missing or unreadable, `load_workspaces()` logs a
warning and returns `{}` rather than raising.

## The Graph Model

A workspace aggregates three things: a dict of `Node`s, a dict of `Rule`s (plus a
separate dict of `inherited_rules`), and a free-form `state` dict.

### Nodes

A `Node` is one entity in the workspace network. Nodes are typed and can be connected
bidirectionally.

```python
from miminions.core.workspace import Node, NodeType

node = Node(
    name="Knowledge Base",
    type=NodeType.KNOWLEDGE,
    properties={"domain": "software"},
    state={"status": "active"},
)
```

`NodeType` values:

| Value | Meaning |
|-------|---------|
| `NodeType.AGENT` | An agent participant |
| `NodeType.TASK` | A unit of work |
| `NodeType.WORKFLOW` | A multi-step process |
| `NodeType.KNOWLEDGE` | A knowledge / data source |
| `NodeType.CUSTOM` | Anything else (the default) |

Connections are **bidirectional** and **idempotent** — `connect_nodes(a, b)` adds each
node to the other's `connections` list, and adding the same edge twice is a no-op.
Removing a node also strips it from every other node's connections.

### Rules

A `Rule` is a `condition → action` pair with a priority. Rules describe *what should
happen* when the workspace state matches a condition.

```python
from miminions.core.workspace import Rule, RulePriority

rule = Rule(
    name="Validate knowledge",
    description="Check confidence before high-priority tasks",
    condition={"type": "state_equals", "key": "task_priority", "value": "high"},
    action={"type": "validate_knowledge", "threshold": 0.7},
    priority=RulePriority.MEDIUM,
)
```

`RulePriority` is an ordered enum — `get_all_rules()` returns enabled rules sorted by
priority **descending**, so `CRITICAL` ranks first:

| Priority | Value |
|----------|-------|
| `RulePriority.LOW` | 1 |
| `RulePriority.MEDIUM` | 2 (default) |
| `RulePriority.HIGH` | 3 |
| `RulePriority.CRITICAL` | 4 |

#### Evaluating rules

`evaluate_state_logic()` walks the enabled rules in priority order, evaluates each
condition against the current `state` / node graph, and **returns a list of matching
action descriptors**. It only reports them — it does not execute anything.

```python
ws.state = {"task_priority": "high"}
for match in ws.evaluate_state_logic():
    print(match["rule_name"], "->", match["action"])
```

!!! warning "The condition engine is basic"
    The built-in condition matcher is intentionally primitive. Only four condition
    `type`s are understood:

    | `type` | Matches when |
    |--------|--------------|
    | `"always"` (or empty `{}`) | always true |
    | `"state_equals"` | `state[key] == value` |
    | `"node_count"` | node count vs `count` using `operator` (`>=` `<=` `==` `>` `<`) |
    | `"node_type_exists"` | a node of `node_type` exists |

    Any other `type` (or an unrecognized `node_count` operator) silently evaluates to
    `False`. There is **no rule-action execution engine** — `evaluate_state_logic()`
    reports applicable actions; running them is up to your code.

#### Rule inheritance

`inherit_rules_from(parent)` copies a parent workspace's rules into this workspace's
`inherited_rules` dict (each as a fresh `Rule` tagged with `inherited_from`), and also
pulls in the parent's own inherited rules. Inherited rules participate in
`get_all_rules()` and `evaluate_state_logic()` alongside the workspace's own rules.

```python
child = manager.create_workspace("child")
child.inherit_rules_from(parent)
print(len(child.inherited_rules))
```

### State and summary

`state` is a plain dict you can read and write directly. `get_network_summary()` returns
a snapshot of the graph:

```python
ws.state["system_load"] = "normal"
ws.get_network_summary()
# {
#   'total_nodes': 2, 'node_types': {'agent': 1, 'task': 1},
#   'total_connections': 1, 'total_rules': 1, 'inherited_rules': 0,
#   'current_state_keys': ['system_load'],
# }
```

## The On-Disk Folder

Persisting the *graph* (via `WorkspaceManager`) is separate from creating the
workspace's *folder*. The folder is the source of truth for the agent's prompt and
memory, and it follows a fixed layout:

```text
<workspace_root>/
├── prompt/      # AGENTS.md, USER.md, TOOLS.md, IDENTITY.md
├── memory/      # MEMORY.md (Tier 2), HISTORY.md (Tier 1)
├── skills/      # <skill>/SKILL.md
├── sessions/    # *.jsonl chat transcripts
└── data/        # agent file boundary / scratch space
```

### Scaffolding a folder

`init_workspace(root, overwrite=False)` creates the directory tree and writes the
template files. It **never overwrites** existing files unless `overwrite=True`, so it is
safe to re-run — it only fills in what is missing.

```python
from miminions.workspace_fs import init_workspace

result = init_workspace("~/.miminions/workspaces/ws_demo")
print(result["created"])   # list of files written
print(result["skipped"])   # list of files already present
print(result["root"])      # resolved absolute root
```

The four bootstrap prompt files are exposed as a constant:

```python
from miminions.workspace_fs import BOOTSTRAP_PROMPT_FILES
# ['AGENTS.md', 'USER.md', 'TOOLS.md', 'IDENTITY.md']
```

### Reading the folder

The same package provides readers used by the [Context Builder](context.md):

```python
from miminions.workspace_fs import read_prompt_files, list_skills

prompts = read_prompt_files("~/.miminions/workspaces/ws_demo")
# {'AGENTS.md': '...', 'USER.md': '...', ...}  — missing files are omitted

skills = list_skills("~/.miminions/workspaces/ws_demo")
# [{'name': 'core', 'path': '.../skills/core/SKILL.md'}]
```

A `WorkspaceLayout` object computes every path for a given root, if you need it directly:

```python
from miminions.workspace_fs import WorkspaceLayout

layout = WorkspaceLayout.from_root("~/.miminions/workspaces/ws_demo")
layout.prompt_dir     # .../prompt
layout.memory_dir     # .../memory
layout.sessions_dir   # .../sessions
```

## Wiring a Workspace into an Agent

Attach a resolved workspace and its on-disk root to a Minion with `set_context()`. On
every `run()`, a system-prompt callback invokes `ContextBuilder().build(workspace, root)`
to inject the identity, prompt files, memory, graph summary, and skills index.

```python
from miminions.agent import create_minion
from miminions.core.workspace import WorkspaceManager, resolve_workspace
from pathlib import Path

manager = WorkspaceManager(Path("~/.miminions").expanduser())
ws = resolve_workspace(manager.load_workspaces(), "research")

agent = create_minion("Assistant")
agent.set_context(ws, root_path=ws.root_path)
# agent.run(...) now builds its system prompt from this workspace.
```

See [Context Builder](context.md) for exactly which sections get emitted.

## First-Run Bootstrap

On first use, MiMinions creates a `"default"` workspace (graph **and** folder) plus a
default agent record under `~/.miminions/`. This is idempotent — later runs cost a
single config read.

```python
from pathlib import Path
from miminions.core.bootstrap import ensure_default_setup

config = ensure_default_setup(Path("~/.miminions").expanduser())
print(config["default_workspace"])  # the default workspace id
print(config["default_agent"])      # "default"
```

`ensure_default_setup` creates the default workspace if absent, assigns it a root under
`<config_dir>/workspaces/ws_<id>`, runs `init_workspace` to scaffold the folder, seeds a
default agent in `agents.json`, and records both ids in `config.json`.

## CLI

The same operations are available from the `miminions workspace` command group, which
stores everything under `~/.miminions/` (override the location with the
`MIMINIONS_HOME` environment variable).

```bash
# Create a workspace and scaffold its folder
miminions workspace add --name research --init-files

# Create a demo workspace with example nodes, rules, and state
miminions workspace add --name demo --sample

# List, inspect, update, remove
miminions workspace list
miminions workspace show research
miminions workspace update research --description "Updated"
miminions workspace remove research

# State and rules
miminions workspace set-state research --key task_priority --value high
miminions workspace add-rule research --name "Has agent" --priority HIGH \
    --condition '{"type":"node_type_exists","node_type":"agent"}' \
    --action '{"type":"assign_task"}'
miminions workspace remove-rule research "Has agent"

# Scaffold the folder for an existing workspace
miminions workspace init-files research
```

See the [CLI reference](cli.md) for the full command set.

## API Reference

### `WorkspaceManager`

`WorkspaceManager(config_dir_path)` — `config_dir_path` must be a `Path`.

| Method | Description |
|--------|-------------|
| `load_workspaces() -> dict[str, Workspace]` | Read `workspaces.json` (migrating each record to the current schema version); returns `{}` if missing or unreadable |
| `save_workspaces(workspaces)` | Atomically write the dict back to `workspaces.json` |
| `create_workspace(name, description="")` | Build a new in-memory `Workspace` (not persisted) |
| `create_sample_workspace()` | Build a demo workspace with example nodes, rules, and state |

### Module functions

| Function | Description |
|----------|-------------|
| `resolve_workspace(workspaces, ref)` | Look up one workspace by id, id prefix, or name; `None` if absent |
| `ensure_workspace(manager, ref, *, create_missing=False, init_files=False)` | Resolve/create a workspace and return `(workspace, root_path)` |
| `ensure_default_setup(config_dir)` | First-run bootstrap: default workspace + agent under `config_dir` |

### `Workspace`

| Method | Description |
|--------|-------------|
| `add_node(node)` / `remove_node(node_id)` | Add or remove a `Node` |
| `connect_nodes(a, b)` / `disconnect_nodes(a, b)` | Manage bidirectional edges |
| `add_rule(rule)` / `remove_rule(rule_id)` | Add or remove a `Rule` |
| `get_all_rules()` | Enabled own + inherited rules, sorted by priority descending |
| `inherit_rules_from(parent)` | Copy a parent workspace's rules into `inherited_rules` |
| `evaluate_state_logic()` | Report (not execute) actions whose conditions match the current state |
| `get_network_summary()` | Node/rule/connection counts and state keys |
| `to_dict()` / `from_dict(data)` | JSON-safe round-trip |

### `miminions.workspace_fs`

| Symbol | Description |
|--------|-------------|
| `init_workspace(root, overwrite=False)` | Scaffold the folder + template files; never overwrites unless asked |
| `read_prompt_files(root)` | `{filename: contents}` for the bootstrap prompt files present |
| `read_memory_md(root)` | Contents of `memory/MEMORY.md`, or `""` if missing |
| `list_skills(root)` | `[{"name", "path"}]` for each `skills/<skill>/SKILL.md` |
| `WorkspaceLayout.from_root(root)` | Path helper exposing `prompt_dir`, `memory_dir`, etc. |
| `BOOTSTRAP_PROMPT_FILES` | `["AGENTS.md", "USER.md", "TOOLS.md", "IDENTITY.md"]` |

## See Also

- [Agent](agent.md) — attach a workspace with `set_context()`
- [Context Builder](context.md) — how the folder becomes a system prompt
- [Memory](memory.md) — the three-tier memory backed by `memory/`
- [CLI](cli.md) — the `miminions workspace` command group
