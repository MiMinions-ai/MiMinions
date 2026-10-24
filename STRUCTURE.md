# MiMinions Repository Structure

This file is a human-readable map of the current repository. Packaging metadata
in `pyproject.toml` remains the source of truth for installed entry points and
dependencies.

```text
MiMinions/
|-- README.md                  # Project overview and quick start
|-- (changelog lives in docs/changelog.md — single canonical copy, on the site)
|-- CONTRIBUTING.md            # Contribution guidelines
|-- CODE_OF_CONDUCT.md         # Community standards
|-- LICENSE                    # MIT license
|-- pyproject.toml             # Packaging, dependencies, console scripts
|-- requirements.txt           # Development/full dependency list
|-- mkdocs.yml                 # Documentation site config
|-- MANIFEST.in                # Source distribution includes
|-- amplify.yml                # Hosting/deployment config
|
|-- deploy/
|   |-- build_cli.sh           # PyInstaller build for the packaged CLI entry point
|   |-- to_pypi.sh             # Publish helper
|   `-- to_pypi_test.sh        # TestPyPI publish helper
|
|-- docs/                      # MkDocs documentation
|   |-- index.md
|   |-- getting-started.md
|   |-- features.md
|   |-- changelog.md
|   |-- (internal docs: roadmap, ADRs, backlog, test notes — private MiMinions-ai/docs-internal repo, never in this tree)
|   |-- architecture/
|   |   `-- recursive-evolution.md  # Recursive, bounded evolution spec (L0 contract)
|   |-- modules/
|   |   |-- agent.md
|   |   |-- cli.md
|   |   |-- context.md
|   |   |-- data.md
|   |   |-- gateway.md
|   |   |-- memory.md
|   |   |-- tasks.md
|   |   |-- tools.md
|   |   `-- workspaces.md
|   |-- use-cases/
|   |-- overrides/
|   `-- stylesheets/
|
|-- scripts/
|   `-- check_structure.py     # Gated check: tree <-> map <-> nav <-> READMEs agree
|
|-- examples/
|   |-- minion_agent_example.py
|   |-- sqlite_memory_example.py
|   |-- document_ingestion_example.py
|   |-- tasks_example.py
|   |-- example_chat/
|   `-- example_files/
|
|-- src/
|   |-- __init__.py
|   `-- miminions/
|       |-- __init__.py        # Package metadata fallback
|       |-- __main__.py        # `python -m miminions`
|       |
|       |-- agent/             # Minion agent runtime
|       |   |-- agent.py       # Minion, create_minion, tools, memory, MCP
|       |   |-- models.py      # AgentConfig, AgentState
|       |   |-- provider.py    # ModelFactory providers
|       |   `-- README.md
|       |
|       |-- cli/               # Click CLI implementation
|       |   |-- main.py        # Root command group and registrations
|       |   |-- auth.py
|       |   |-- agent.py
|       |   |-- chat.py
|       |   |-- execution.py
|       |   |-- gateway.py     # Registered as `miminions gateway`
|       |   |-- knowledge.py
|       |   |-- prompt.py
|       |   |-- task.py
|       |   |-- tool.py       # Registered as `miminions tool`
|       |   |-- workspace.py
|       |   |-- workflow.py    # Internal-only workflow helpers; not a shipped CLI command
|       |   |-- config.py      # Registered as `miminions config`
|       |   |-- instance.py    # Registered as `miminions instance`
|       |   |-- transfer.py    # Registered as `miminions export` / `import`
|       |   |-- dispatch.py, persistence.py  # Internal CLI plumbing
|       |   `-- README.md
|       |
|       |-- context/           # System-prompt assembly
|       |   |-- context_builder.py
|       |   |-- strategies.py    # Per-section compaction strategies
|       |   `-- README.md
|       |
|       |-- core/              # Shared domain/runtime primitives
|       |   |-- auth.py
|       |   |-- bootstrap.py
|       |   |-- paths.py, persistence.py  # Config-home paths, JSON persistence
|       |   |-- workspace.py
|       |   |-- gateway/       # Bus, channels, sessions, cron, orchestrator
|       |   `-- README.md
|       |
|       |-- data/              # Local content-addressable data manager
|       |   |-- local/
|       |   `-- README.md
|       |
|       |-- memory/            # Markdown and SQLite memory backends
|       |   |-- base_memory.py
|       |   |-- budget.py        # Memory budgets and pressure checks
|       |   |-- compaction.py    # Memory compaction
|       |   |-- dedupe.py        # Context deduplication
|       |   |-- distiller.py
|       |   |-- llm_filter.py
|       |   |-- md_store.py
|       |   |-- sqlite.py
|       |   |-- types.py
|       |   `-- README.md
|       |
|       |-- execution/         # Durable local execution (persistent worker)
|       |   |-- models.py        # ExecutionRequest, ExecutionTask, TaskEvent, TaskHandle
|       |   |-- service.py       # ExecutionService client API
|       |   |-- store.py, worker.py, processes.py, handlers.py
|       |   `-- README.md
|       |
|       |-- session/           # JSONL chat transcript store
|       |   |-- store.py         # JsonlSessionStore, create_session_id
|       |   `-- README.md
|       |-- task/              # Task models and async runtime (in-memory)
|       |   |-- model.py         # Task, AgentTask, TaskStatus, TaskPriority
|       |   |-- control.py       # TaskRuntime
|       |   `-- README.md
|       |-- tools/             # Generic tools, schemas, MCP adapter
|       |   |-- __init__.py      # GenericTool, create_tool, tool, ToolSchema (dataclass)
|       |   |-- schemas.py       # Pydantic ToolSchema (internal) + ToolDefinition
|       |   `-- README.md
|       |-- user/              # User dataclass and stub controller
|       |   `-- README.md
|       |-- utils/             # Chunking, generators, session helpers
|       |   `-- README.md
|       |-- workflow/          # Workflow trace models and controller (internal; no public surface)
|       |   `-- README.md
|       `-- workspace_fs/      # On-disk workspace layout and readers
|           |-- layout.py        # WorkspaceLayout, BOOTSTRAP_PROMPT_FILES
|           |-- bootstrap.py     # init_workspace scaffolding
|           |-- reader.py        # Prompt/memory/skills readers
|           `-- README.md
|
`-- tests/
    |-- README.md
    |-- unit/
    |-- integration/
    `-- e2e/
```

## CLI Entry Points

- Installed console script: `miminions = "miminions.cli.main:main"`.
- Module execution: `python -m miminions`, via `src/miminions/__main__.py`.
- The root-level `main.py` wrapper was removed; build scripts should use the
  packaged entry point.

Registered CLI command groups are:

```text
auth, agent, tool, task, instance, knowledge, workspace, chat, gateway, prompt, config, export, import
```

`src/miminions/cli/workflow.py` remains in the tree for internal workflow-related
helpers, but `src/miminions/cli/main.py` does not ship a `miminions workflow`
command group.

## Public Import Surface

Prefer concrete subpackage imports:

```python
from miminions.agent import create_minion, Minion
from miminions.tools import GenericTool, create_tool, tool, ToolSchema
from miminions.memory.sqlite import SQLiteMemory
from miminions.memory import MemoryDistiller, create_llm_filter
from miminions.context import ContextBuilder
from miminions.core.workspace import WorkspaceManager, Workspace, Node, Rule
from miminions.workspace_fs import WorkspaceLayout, init_workspace
from miminions.data import LocalDataManager
from miminions.task import TaskRuntime, Task, AgentTask
from miminions.execution import ExecutionService, ExecutionRequest
from miminions.session import JsonlSessionStore, create_session_id
from miminions.core.gateway import MessageBus, ChannelManager, CronService
```

The top-level package exposes version metadata, but most runtime APIs should be
imported from their subpackages.

## Notes

- `store_knowledge()` and `recall_knowledge()` are real `Minion` helpers backed
  by the attached memory backend.
- `SQLiteMemory` requires the `sqlite` extra and lives at
  `miminions.memory.sqlite`.
- Evolution is governed by [Recursive, Bounded Evolution](docs/architecture/recursive-evolution.md):
  every module carries a five-block contract (Purpose / Public surface / State /
  Lifecycle / Gate) in its `README.md`, and `scripts/check_structure.py` fails CI
  when this map, the tracked tree, the MkDocs nav, and the CLI groups disagree.
- `chat`, `prompt`, and gateway runtime paths use workspace files under
  `~/.miminions/` by default.
