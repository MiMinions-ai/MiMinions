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
|       |-- core/              # Domain/runtime primitives
|       |   |-- agent/         # Minion, models, providers
|       |   |   `-- memory/    # BaseMemory, memory types and public memory helpers
|       |   |-- context/       # Prompt assembly, budgets, compaction, distillation
|       |   |-- knowledge/     # Reserved package
|       |   |-- task/          # In-memory task models and TaskRuntime
|       |   |-- tool/          # Generic tools, schemas, MCP, approved project tools
|       |   |-- workspace/
|       |   |   |-- registry.py  # Workspace, Node, Rule, WorkspaceManager, resolvers
|       |   |   |-- discovery.py # Bounded AST discovery and metadata cache
|       |   |   |-- layout.py    # WorkspaceLayout, BOOTSTRAP_PROMPT_FILES
|       |   |   |-- bootstrap.py # init_workspace scaffolding
|       |   |   `-- reader.py    # Prompt/memory/skills readers
|       |   |-- paths.py, persistence.py
|       |   `-- README.md
|       |
|       |-- daemon/            # Bus, channels, sessions, cron and orchestration
|       |   `-- README.md
|       |
|       |-- interface/
|       |   |-- bootstrap.py   # First-run setup
|       |   |-- config.py      # Registered as `miminions config`
|       |   |-- session.py     # JsonlSessionStore and history helpers
|       |   |-- gui/           # Reserved package
|       |   |-- cli/
|       |   |   |-- main.py    # Lazy root command registrations
|       |   |   |-- auth.py, daemon.py
|       |   |   |-- management/ # agent, instance, knowledge, project, task, tool,
|       |   |   |               # workspace and internal workflow helpers
|       |   |   |-- operations/ # chat, prompt, dispatch, execution
|       |   |   `-- transfer/   # export/import commands
|       |   `-- README.md
|       |
|       |-- system/
|       |   |-- auth/          # Local authentication helpers
|       |   |-- config/        # Reserved package
|       |   |-- db/            # SQLiteMemory backend
|       |   |-- execution/     # Durable worker, service, store, handlers and traces
|       |   |-- file/          # Content-addressable storage and Markdown memory IO
|       |   `-- README.md
|       |
|       `-- utils/             # Chunking, generators and JSON helpers
|           `-- README.md
|
`-- tests/
    |-- README.md
    |-- unit/
    |-- integration/
    `-- e2e/
```

## CLI Entry Points

- Installed console script: `miminions = "miminions.interface.cli.main:main"`.
- Module execution: `python -m miminions`, via `src/miminions/__main__.py`.
- The root-level `main.py` wrapper was removed; build scripts should use the
  packaged entry point.

Registered CLI command groups are:

```text
auth, agent, tool, task, instance, knowledge, workspace, chat, gateway, prompt, config, export, import
(plus the standalone `init` bootstrap command, eagerly registered in `interface/cli/main.py` — 14 top-level entry points in total)
```

`src/miminions/interface/cli/management/workflow.py` remains in the tree for internal workflow-related
helpers, but `src/miminions/interface/cli/main.py` does not ship a `miminions workflow`
command group.

## Public Import Surface

Prefer concrete subpackage imports:

```python
from miminions.core.agent import create_minion, Minion
from miminions.core.tool import GenericTool, create_tool, tool, ToolSchema
from miminions.system.db.sqlite import SQLiteMemory
from miminions.core.agent.memory import MemoryDistiller, create_llm_filter
from miminions.core.context import ContextBuilder
from miminions.core.workspace import WorkspaceManager, Workspace, Node, Rule
from miminions.core.workspace import WorkspaceLayout, init_workspace
from miminions.system import LocalDataManager
from miminions.core.task import TaskRuntime, Task, AgentTask
from miminions.system.execution import ExecutionService, ExecutionRequest
from miminions.interface.session import JsonlSessionStore, create_session_id
from miminions.daemon import MessageBus, ChannelManager, CronService
```

The top-level package exposes version metadata, but most runtime APIs should be
imported from their subpackages.

The reorganized packages are canonical; update old `miminions.agent`,
`miminions.cli`, `miminions.memory`, and other pre-reorganization imports to
the paths above. Workspace models and filesystem helpers share
`miminions.core.workspace`; their implementations live in separate modules
inside that package, avoiding a same-name `workspace.py`/`workspace/` collision.

## Notes

- `store_knowledge()` and `recall_knowledge()` are real `Minion` helpers backed
  by the attached memory backend.
- `SQLiteMemory` requires the `sqlite` extra and lives at
  `miminions.system.db.sqlite`.
- Evolution is governed by [Recursive, Bounded Evolution](docs/architecture/recursive-evolution.md):
  every module carries a five-block contract (Purpose / Public surface / State /
  Lifecycle / Gate) in its `README.md`, and `scripts/check_structure.py` fails CI
  when this map, the tracked tree, the MkDocs nav, and the CLI groups disagree.
- `chat`, `prompt`, and gateway runtime paths use workspace files under
  `~/.miminions/` by default.
