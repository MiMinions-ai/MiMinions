# Changelog

<!-- markdownlint-disable MD024 -->

All notable changes to MiMinions are documented here.

The format follows [Keep a Changelog](https://keepachangelog.com/en/1.0.0/) and the project adheres to [Semantic Versioning](https://semver.org/).

!!! tip "Current version"
    The latest published release is **0.4.1** (requires Python &ge; 3.12). Install it with `pip install miminions`, or `pip install miminions[sqlite]` to add SQLite vector memory. See [Getting Started](getting-started.md) for the full matrix.

## [Unreleased]

Work in progress toward the next release.

### Added

- TBD

## [0.4.1] - 2026-08-26

Latest published release on PyPI.

### Changed

- `miminions agent run` no longer accepts the non-functional `--async` flag; the CLI now fails fast instead of exposing a placeholder execution path.
- `miminions agent run` and `miminions agent ask` now send prompts straight through the runtime model instead of applying hidden keyword-based demo tool routing.
- Workflow-related CLI code remains internal-only; public docs no longer imply a shipped `miminions workflow` command surface.

## [0.4.0] - 2026-08-24

Latest published release on PyPI.

### Added

- **Streaming replies.** `Minion.run_stream()` yields the LLM reply as incremental text deltas; the CLI `chat` loop now streams every reply to the terminal. See [Agent](modules/agent.md#streaming-replies).
- **Retries, timeouts, and observability hooks.** `create_minion` accepts `request_timeout` (per-HTTP-request, default 60 s), `max_retries` (default 2) with exponential backoff on transient provider errors (429/5xx, connection failures), and optional `on_tool_call` / `on_turn_end` callbacks. `miminions chat start --verbose` uses them to show tool calls, token usage, and latency per turn.
- **Message-history trimming.** `trim_message_history` caps the LLM context for long chat sessions at 40 messages, cutting only at user-turn boundaries so tool call/return pairs are never split; the on-disk transcript stays complete.
- **Workspace schema versioning.** Persisted workspace records carry a `schema_version` field (currently 1) with a migration hook at load time; unversioned records are treated as v1 and stamped on the next save.
- **`SQLiteMemory` as a context manager.** `with SQLiteMemory(...) as mem:` closes the connection automatically.
- **Centralized path resolution** (`miminions.core.paths`). All persistent state resolves through `get_config_dir()`, honoring a new `MIMINIONS_HOME` environment variable to relocate `~/.miminions`. `get_global_memory_db_path` moved here (still re-exported from `miminions.memory.sqlite`).

### Changed

- **Atomic JSON persistence.** Shared `load_json` / `save_json` helpers (`miminions.core.persistence`) write all CLI/JSON stores atomically and fail loudly on corrupt files.
- **Fail-fast OpenRouter key check.** With the default `openrouter` provider, a missing `OPENROUTER_API_KEY` now raises `ValueError` at `create_minion(...)` construction instead of failing later at call time.
- `miminions agent add` derives unique agent ids: a name collision gets a `_2`, `_3`, … suffix instead of an error, and `created_at` is now a real UTC timestamp.
- Chat errors preserve any partially streamed reply in the session transcript alongside the `[error]` marker.

## [0.3.0]

Previous published release on PyPI.

### Added

- **Click-based CLI** (`miminions` / `python -m miminions`) with nine command groups: `auth`, `agent`, `task`, `knowledge`, `workspace`, `execution`, `chat`, `gateway`, and `prompt`. State persists locally under `~/.miminions/`. See [CLI](modules/cli.md).
- **First-run bootstrap.** `miminions.core.bootstrap.ensure_default_setup` idempotently creates a `default` workspace and a default agent record under `~/.miminions/` on first use, so the CLI works out of the box.
- **Three-tier memory with an LLM distiller.** A chronological session log (`HISTORY.md`), stable workspace facts (`MEMORY.md` &rarr; "Project Facts"), and a cross-workspace SQLite vector store (`~/.miminions/global_memory.db`). `MemoryDistiller` extracts and promotes insights across tiers using an `create_llm_filter`-built extractor. See [Memory](modules/memory.md).
- **Workspace system.** A node/rule graph model (`Workspace`, `Node`, `Rule`, `NodeType`, `RulePriority`) with rule inheritance and priority-sorted evaluation, a JSON-backed `WorkspaceManager`, and an on-disk layout (`prompt/`, `memory/`, `skills/`, `sessions/`, `data/`) scaffolded by `init_workspace`. See [Workspaces](modules/workspaces.md).
- **Context injection.** `ContextBuilder().build(workspace, root_path)` composes a single markdown context block (Identity, Tool Boundary, Prompt Files, optional Global Knowledge, Memory, Workspace Graph Summary, Skills Index) that is wired into the agent system prompt via `Minion.set_context`. See [Context](modules/context.md).
- **MCP tool loading.** Connect to a stdio MCP server with `await agent.connect_mcp_server(name, StdioServerParameters(...))` and register its tools with `await agent.load_tools_from_mcp_server(name)`. Uses the `mcp` package, which is a core dependency. See [Agent](modules/agent.md).
- **Gateway runtime building blocks** (`miminions.core.gateway`): an async pub/sub `MessageBus`, a `BaseChannel` abstraction, a JSONL `SessionManager`, a `CronService` (one-shot, recurring, and cron-expression schedules; cron expressions require the optional `croniter` package), and a phased `GatewayOrchestrator`. Provided as an extensible runtime layer, not a turnkey server. See [Gateway](modules/gateway.md).
- **Workflow tracing models** (`WorkflowTrace`, `WorkflowRun`, `ToolCallRecord`, `AgentRunRecord`) and a `WorkflowController`, persisted by the `miminions execution` CLI.

### Changed

- **Replaced `sentence-transformers` with `fastembed`** (ONNX Runtime) for `SQLiteMemory` embeddings, removing the PyTorch/CUDA dependency. Same `all-MiniLM-L6-v2` model and 384-dim output, so existing databases need no migration. SQLite vector memory now installs via the `[sqlite]` (or `[all]`) extra alongside `sqlite-vec` and `pysqlite3`.
- Simplified the user module to a lean `User` dataclass (`miminions.user.model`).

### Removed

- Heavy embedding stack (PyTorch/CUDA) is no longer pulled in for SQLite vector memory.
- Complex user authentication and validation systems.

!!! note "Not yet enabled"
    A `workflow` CLI command group exists in the tree but is **not registered** ("not yet implemented"). The `--async` flag on `miminions agent run` is currently a no-op placeholder. These are tracked for a future release and are documented as planned, not present.

## [0.2.2] - 2026-04-02

### Added

- Agent layer built on `pydantic_ai`: `create_minion` / `Minion` with a tool registry, optional vector memory (auto-registering seven memory + ingestion tools), and an async `run()` reasoning loop.
- `ModelFactory` provider selection &mdash; `openrouter` (default, `openai/gpt-oss-20b:free`), `openai`, `anthropic`, `gemini`, and an offline `test` model.
- `SQLiteMemory` vector store with vector, keyword, full-text, metadata, regex, hybrid, and date-range search, backed by `sqlite-vec`.
- `GenericTool` / `@tool` / `create_tool` tool abstraction and an MCP tool adapter.
- `LocalDataManager` content-addressable (SHA-256) local storage with deduplication, a JSON master index, and an append-only transaction log.

## [0.1.0]

Initial release.

### Added

- Core MiMinions package structure.
- Generic tool system and agent management foundations.
- Local data management system.
- User module with a basic data model.
- A test suite structure.

---

## Version history

| Version | Notes |
| ------- | ----- |
| **Unreleased** | TBD |
| **0.4.1** | Current published release &mdash; removes the no-op `agent run --async` flag and hidden keyword-based CLI prompt bypass |
| **0.4.0** | Previous release &mdash; streaming replies, retries + timeouts + hooks, history trimming, workspace schema versioning, `MIMINIONS_HOME`, atomic JSON persistence |
| **0.3.0** | CLI, three-tier memory + distiller, workspaces, context builder, MCP loading, gateway building blocks; `fastembed` embeddings |
| **0.2.2** | Agent, vector memory, tools, local data |
| **0.1.0** | Initial release with core functionality |

---

## How to read this changelog

### Categories

- **Added** &mdash; new features
- **Changed** &mdash; changes to existing functionality
- **Deprecated** &mdash; features slated for removal
- **Removed** &mdash; features that have been removed
- **Fixed** &mdash; bug fixes
- **Security** &mdash; security-related changes

### Versioning

We follow [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):

- **MAJOR** &mdash; incompatible API changes
- **MINOR** &mdash; new functionality, backward-compatible
- **PATCH** &mdash; backward-compatible bug fixes

## Contributing

When adding changelog entries:

1. Add the entry under the appropriate category.
2. Use clear, concise language.
3. Reference issue numbers where applicable.
4. Keep the **Unreleased** section current as development proceeds.

See [Contributing](contributing.md) for the full workflow.
