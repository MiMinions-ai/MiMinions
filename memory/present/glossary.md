# Glossary

Domain vocabulary as used in this codebase. Where a term is ordinary English
with a narrowed meaning here, the narrowing is what matters.

**Minion** — the agent runtime object, created by `create_minion()`. Wraps a
model, optional tools, an optional memory backend, and optional MCP servers.
The unit that actually talks to an LLM.

**Agent** — in CLI context (`miminions agent ...`), a *persisted record* of an
agent configuration, not a live `Minion`. Agents have ids, names, and
`created_at` timestamps and live in JSON under `~/.miminions`. A `Minion` is
constructed from one at run time. The two words are not interchangeable.

**Workspace** — a named collection of nodes and rules describing a working
context. Persisted records carry `schema_version`. Distinct from
`workspace_fs`, which is the on-disk layout and reader layer beneath it.

**Node** / **Rule** — the constituent parts of a `Workspace`.

**Memory** — durable knowledge attached to a `Minion`, written with
`store_knowledge()` and read with `recall_knowledge()`. Two backends exist:
markdown (`md_store`) and vector (`SQLiteMemory`, behind the `sqlite` extra).
Not the same as session history.

**Session** — the JSONL transcript of a chat conversation. Complete on disk even
when the model's context has been trimmed. Distinct from memory: sessions are a
verbatim log, memory is curated recall.

**Message-history trimming** — capping what is *sent to the model* at 40
messages, cut only at user-turn boundaries so tool call/return pairs are never
split. Affects the request, never the stored transcript.

**Distiller** / **LLM filter** — memory-layer components that condense or screen
what gets retained.

**Context builder** — assembles the system prompt from workspace, memory, and
configuration. The `context` subpackage.

**Task** — a unit of asynchronous work in the `task` subpackage, executed by
`TaskRuntime`. `AgentTask` is the agent-backed variant.

**Workflow** — trace models and a controller in the `workflow` subpackage.
Internal-only: no CLI command group ships, and nothing else imports it. Do not
assume a user-facing workflow feature exists.

**Gateway** — the messaging layer under `core/gateway`: message bus, channels,
sessions, cron service, orchestrator.

**Tool** — a callable exposed to the model, via `GenericTool`, the `@tool`
decorator, or an MCP server through the MCP adapter.

**MCP** — Model Context Protocol. External tool servers a `Minion` can attach.

**Provider** — an LLM backend selected through `ModelFactory`. Default is
`openrouter`, which fails fast at `create_minion()` if `OPENROUTER_API_KEY` is
unset.

**`MIMINIONS_HOME`** — environment variable relocating the default
`~/.miminions` state directory. All paths resolve through
`core.paths.get_config_dir()`.
