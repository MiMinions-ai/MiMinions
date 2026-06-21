# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

The latest published release is **0.2.2** (requires Python ≥ 3.12). Install with
`pip install miminions`, or `pip install miminions[sqlite]` for SQLite vector memory.

## [Unreleased]

Work in progress toward the next release.

### Added

- **Click-based CLI** (`miminions` / `python -m miminions`) with eight command
  groups: `auth`, `agent`, `task`, `knowledge`, `workspace`, `execution`,
  `chat`, and `prompt`. State persists locally under `~/.miminions/`.
- **First-run bootstrap.** `ensure_default_setup` idempotently creates a
  `default` workspace and a default agent under `~/.miminions/`, so the CLI works
  out of the box.
- **Three-tier memory with an LLM distiller.** A chronological session log
  (`HISTORY.md`), stable workspace facts (`MEMORY.md`), and a cross-workspace
  SQLite vector store (`~/.miminions/global_memory.db`). `MemoryDistiller`
  extracts and promotes insights across tiers using an `create_llm_filter`-built
  extractor.
- **Workspace system.** A node/rule graph model (`Workspace`, `Node`, `Rule`,
  `NodeType`, `RulePriority`) with rule inheritance and priority-sorted
  evaluation, a JSON-backed `WorkspaceManager`, and an on-disk layout
  (`prompt/`, `memory/`, `skills/`, `sessions/`, `data/`) scaffolded by
  `init_workspace`.
- **Context injection.** `ContextBuilder().build(workspace, root_path)` composes
  a single markdown context block (Identity, Tool Boundary, Prompt Files,
  optional Global Knowledge, Memory, Workspace Graph Summary, Skills Index),
  wired into the agent system prompt via `Minion.set_context`.
- **MCP tool loading.** `await agent.connect_mcp_server(name, StdioServerParameters(...))`
  followed by `await agent.load_tools_from_mcp_server(name)`. Uses the `mcp`
  package, which is a core dependency.
- **Gateway runtime building blocks** (`miminions.core.gateway`): an async
  pub/sub `MessageBus`, a `BaseChannel` abstraction, a JSONL `SessionManager`, a
  `CronService` (one-shot, recurring, and cron-expression schedules; cron
  expressions require the optional `croniter` package), and a phased
  `GatewayOrchestrator`. Provided as an extensible runtime layer, not a turnkey
  server.
- **Workflow tracing models** (`WorkflowTrace`, `WorkflowRun`, `ToolCallRecord`,
  `AgentRunRecord`) and a `WorkflowController`, persisted by the
  `miminions execution` CLI.

### Changed

- **Replaced `sentence-transformers` with `fastembed`** (ONNX Runtime) for
  `SQLiteMemory` embeddings, removing the PyTorch/CUDA dependency. Same
  `all-MiniLM-L6-v2` model and 384-dim output, so existing databases need no
  migration. SQLite vector memory now installs via the `[sqlite]` (or `[all]`)
  extra alongside `sqlite-vec` and `pysqlite3`.
- Simplified the user module to a lean `User` dataclass.

### Removed

- Heavy embedding stack (PyTorch/CUDA) for SQLite vector memory.
- Complex user authentication and validation systems.

> **Not yet enabled:** a `workflow` CLI command group exists in the tree but is
> not registered ("not yet implemented"), and the `--async` flag on
> `miminions agent run` is a no-op placeholder. Both are documented as planned,
> not present.

## [0.2.2]

Current published release on PyPI.

### Added

- Agent layer built on `pydantic-ai`: `create_minion` / `Minion` with a tool
  registry, optional vector memory (auto-registering seven memory + ingestion
  tools), and an async `run()` reasoning loop.
- `ModelFactory` provider selection — `openrouter` (default,
  `openai/gpt-oss-20b:free`), `openai`, `anthropic`, `gemini`, and an offline
  `test` model.
- `SQLiteMemory` vector store with vector, keyword, full-text, metadata, regex,
  hybrid, and date-range search, backed by `sqlite-vec`.
- `GenericTool` / `@tool` / `create_tool` tool abstraction and an MCP tool adapter.
- `LocalDataManager` content-addressable (SHA-256) local storage with
  deduplication, a JSON master index, and an append-only transaction log.

## [0.1.0]

Initial release.

### Added

- Core MiMinions package structure.
- Generic tool system and agent management foundations.
- Local data management system.
- User module with a basic data model.
- A test suite structure.

---

## Version History

| Version | Notes |
|---------|-------|
| **Unreleased** | CLI, three-tier memory + distiller, workspaces, context builder, MCP loading, gateway building blocks; `fastembed` embeddings |
| **0.2.2** | Current published release — agent, vector memory, tools, local data |
| **0.1.0** | Initial release with core functionality |

## How to Read This Changelog

Categories: **Added** (new features), **Changed** (changes to existing
functionality), **Deprecated** (slated for removal), **Removed** (removed
features), **Fixed** (bug fixes), **Security** (security-related changes).

We follow [Semantic Versioning](https://semver.org/) (`MAJOR.MINOR.PATCH`):
MAJOR for incompatible API changes, MINOR for backward-compatible features, and
PATCH for backward-compatible bug fixes. Keep the **Unreleased** section current
as development proceeds. See [CONTRIBUTING.md](CONTRIBUTING.md) for the workflow.
