# MiMinions Repository Structure

This file is a human-readable map of the current repository. Packaging metadata
in `pyproject.toml` remains the source of truth for installed entry points and
dependencies.

```text
MiMinions/
|-- README.md                  # Project overview and quick start
|-- CHANGELOG.md               # Version history
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
|   `-- stylesheets/
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
|       |   |-- workspace.py
|       |   |-- workflow.py    # Internal-only workflow helpers; not a shipped CLI command
|       |   `-- README.md
|       |
|       |-- context/           # System-prompt assembly
|       |   |-- context_builder.py
|       |   `-- README.md
|       |
|       |-- core/              # Shared domain/runtime primitives
|       |   |-- auth.py
|       |   |-- bootstrap.py
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
|       |   |-- distiller.py
|       |   |-- llm_filter.py
|       |   |-- md_store.py
|       |   |-- sqlite.py
|       |   |-- types.py
|       |   `-- README.md
|       |
|       |-- session/           # JSONL chat transcript store
|       |-- task/              # Task models and async runtime
|       |-- tools/             # Generic tools, schemas, MCP adapter
|       |-- user/              # User dataclass and stub controller
|       |-- utils/             # Chunking, generators, session helpers
|       |-- workflow/          # Workflow trace models and controller
|       `-- workspace_fs/      # On-disk workspace layout and readers
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
auth, agent, task, knowledge, workspace, execution, chat, gateway, prompt
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
from miminions.core.gateway import MessageBus, ChannelManager, CronService
```

The top-level package exposes version metadata, but most runtime APIs should be
imported from their subpackages.

## Notes

- `store_knowledge()` and `recall_knowledge()` are real `Minion` helpers backed
  by the attached memory backend.
- `SQLiteMemory` requires the `sqlite` extra and lives at
  `miminions.memory.sqlite`.
- `chat`, `prompt`, and gateway runtime paths use workspace files under
  `~/.miminions/` by default.
