# Memory System Guide

How MiMinions stores, evolves, and injects memory across sessions and workspaces.

---

## Overview: Three-Tier Memory

Memory is split into three layers, from most local to most global:

| Tier | Storage | Scope | What goes in it |
|---|---|---|---|
| **1** | `memory/HISTORY.md` | Per-workspace | One-line log of each session in this workspace |
| **2** | `memory/MEMORY.md` | Per-workspace | Stable facts, decisions, and conventions for this workspace |
| **3** | `~/.miminions/global_memory.db` | Cross-workspace | Reusable insights that apply to any project |

**Core rule:** Markdown is the source of truth. SQLite is a read-only index. The LLM decides what's worth remembering — the app just routes it.

---

## Workspace File Layout

Every workspace lives at a `root_path` on disk:

```
<workspace_root>/
  prompt/
    AGENTS.md       ← agent behavioral rules
    USER.md         ← user preferences
    TOOLS.md        ← tool safety constraints
    IDENTITY.md     ← workspace identity/goals
  memory/
    MEMORY.md       ← Tier 2: stable workspace facts
    HISTORY.md      ← Tier 1: session log for this workspace
  skills/
    core/SKILL.md   ← skill guidance files
  sessions/
    <session_id>.jsonl  ← raw message logs, one file per session
  data/             ← agent's sandboxed write area

~/.miminions/
    global_memory.db    ← Tier 3: cross-workspace SQLite
```

Each workspace is fully isolated. The only thing shared across workspaces is `global_memory.db`.

---

## Full Data Flow

### Session Start — Read Path (ContextBuilder)

`ContextBuilder.build()` is called **once at session startup**. It assembles the full system prompt string passed to the agent for every message in that session.

```
prompt/*.md            → ## Prompt Files
global_memory.db       → ## Global Knowledge   (top-k recent insights, skipped if DB unavailable)
memory/MEMORY.md       → ## Memory
workspace graph/skills → ## Workspace Graph Summary, ## Skills Index
```

The context does **not** rebuild per message — the same string is reused for the entire session.

### During the Session — Messages

Each user/assistant turn is appended to `sessions/<session_id>.jsonl`:

```json
{"timestamp": "...", "session_id": "...", "role": "user", "content": "...", "meta": {"source": "cli-chat"}}
```

Nothing in memory is written during a session. The JSONL file is append-only and never modified.

### Session End — Write Path (Distiller)

When the session ends (any exit: `quit`, `exit`, EOF, Ctrl+C), the `finally` block in `chat.py` triggers distillation exactly once.

```
sessions/<session_id>.jsonl
         │
         ▼  compacted to last 80 messages, 500 chars/message
   llm_filter(transcript, workspace, ...)
         │
         │  returns:
         │  { history_summary, workspace_facts, global_insights }
         │
         ├── history_summary  → appended to memory/HISTORY.md        (Tier 1)
         ├── workspace_facts  → upserted into memory/MEMORY.md       (Tier 2)
         └── global_insights  → inserted into global_memory.db       (Tier 3)
```

Distiller failures are caught and printed as warnings — they never block session exit or crash the chat.

---

## File Roles

### `distiller.py` — The Write Path

`MemoryDistiller` accepts one required callable: `llm_filter`. It:

1. Loads the session transcript from `sessions/*.jsonl`
2. Compacts it (last 80 messages, 500 char cap per message)
3. Calls `llm_filter(transcript=..., workspace=..., root_path=..., session_id=...)`
4. Normalizes and dedupes each output list (exact case-folded match only)
5. Writes to each tier via `md_store` and `SQLiteMemory`

Missing or partial LLM output never crashes — all fields default to empty.

**Why a factory (`create_llm_filter`)?**
We use `create_llm_filter(model)` to generate the filter function rather than defining a hardcoded `llm_filter` function. This is a dependency injection pattern (a closure). It allows `MemoryDistiller` to remain completely agnostic about the LLM provider, `pydantic_ai`, or any API keys. The distiller simply calls `llm_filter(transcript)` exactly as expected, while the function internally remembers and uses the exact model configuration the active agent was instantiated with.

### `md_store.py` — Tier 1 and Tier 2 I/O

| Function | What it does |
|---|---|
| `read_memory(root)` | Reads `MEMORY.md`, creates from template if missing |
| `append_history(root, line)` | Appends `- <line>` to `HISTORY.md` |
| `upsert_memory_section(root, heading, bullets)` | Replaces a `## Section` in `MEMORY.md`, or appends it if new |

`upsert_memory_section` keeps Tier 2 idempotent — re-distilling the same facts overwrites rather than duplicates.

### `sqlite.py` — Tier 3 Storage

`SQLiteMemory` is a vector + keyword search store backed by SQLite with the `sqlite-vec` extension. Each global insight is stored with provenance metadata:

```json
{
  "tier": 3,
  "workspace_id": "...",
  "workspace_name": "...",
  "session_id": "...",
  "source": "distiller",
  "created_at": "..."
}
```

The global DB is always at `~/.miminions/global_memory.db`.

### `context_builder.py` — The Read Path

`ContextBuilder(global_top_k=5, global_db_path=None)` assembles the system prompt. Config:

- `global_top_k` — number of global insights to inject (set to `0` to disable entirely)
- `global_db_path` — override the default DB path

`_fetch_global_insights()` catches all exceptions and returns `[]` — context always builds even if SQLite is missing or broken.

---

## Memory vs. History

A common point of confusion:

| | `MEMORY.md` | `HISTORY.md` |
|---|---|---|
| **Contains** | Stable facts and decisions | Chronological session log |
| **Shape** | Sectioned (`## Project Facts`) | Flat append-only bullet list |
| **Updated** | Upserted (section replaced each time) | Appended (never modified) |
| **Read by agent** | Yes — injected into every session via `## Memory` | No — not read by ContextBuilder |
| **Purpose** | "What is always true about this workspace" | Human-readable audit trail |

Both are **per-workspace**. There is no cross-workspace history file. Cross-workspace sharing happens only through Tier 3 (SQLite).

---

## Workspace Registry

Workspaces are registered in `~/.config/miminions/workspaces.json` (managed by `WorkspaceManager`). Each entry records the workspace `id`, `name`, `root_path`, nodes, rules, and state. You select a workspace at session start via `--workspace <name or id>`.

`root_path` is the single key that scopes all file I/O — every read and write (sessions, memory, history, prompts, skills) resolves paths relative to it. The distiller, context builder, and session store all accept `root_path` explicitly, so there is never ambiguity about which workspace is being accessed or updated.
