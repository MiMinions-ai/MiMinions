# MiMinions Repository Structure

```
MiMinions/
├── 📄 README.md                    # Project overview and quick start
├── 📄 CHANGELOG.md                 # Version history
├── 📄 CONTRIBUTING.md              # Contribution guidelines
├── 📄 CODE_OF_CONDUCT.md           # Community standards
├── 📄 LICENSE                      # MIT license
├── 📄 pyproject.toml               # Packaging & dependencies (source of truth)
├── 📄 requirements.txt             # Dev/full dependency list (not the install contract)
├── 📄 mkdocs.yml                   # Documentation site config
├── 📁 docs/                        # MkDocs documentation (published to miminions.ai)
├── 📁 deploy/                      # build_cli.sh, to_pypi.sh helpers
│
├── 📁 src/
│   └── 📁 miminions/               # Main package
│       ├── 📄 __init__.py
│       ├── 📄 __main__.py          # `python -m miminions` entry point
│       │
│       ├── 📁 agent/               # ✅ Minion agent (pydantic-ai)
│       │   ├── 📄 agent.py             # Minion + create_minion
│       │   ├── 📄 models.py            # AgentConfig, AgentState
│       │   └── 📄 provider.py          # ModelFactory (openrouter/openai/anthropic/gemini/test)
│       │
│       ├── 📁 cli/                 # ✅ Click CLI (entry point: cli/main.py)
│       │   ├── 📄 main.py              # Root group + command registration
│       │   ├── 📄 auth.py              # signin/signout/status/config (local)
│       │   ├── 📄 agent.py             # agent management + tool run/inspect
│       │   ├── 📄 chat.py              # interactive chat loop
│       │   ├── 📄 prompt.py            # one-shot prompt
│       │   ├── 📄 task.py              # task CRUD
│       │   ├── 📄 knowledge.py         # versioned knowledge base
│       │   ├── 📄 workspace.py         # workspace + node/rule commands
│       │   ├── 📄 execution.py         # execution sessions + tool runs
│       │   └── 📄 workflow.py          # 🚧 written but NOT registered in main.py
│       │
│       ├── 📁 context/             # ✅ ContextBuilder (system-prompt assembly)
│       │   └── 📄 context_builder.py
│       │
│       ├── 📁 core/                # Domain core
│       │   ├── 📄 auth.py              # ✅ require_auth decorator
│       │   ├── 📄 bootstrap.py         # ✅ ensure_default_setup (first-run)
│       │   ├── 📄 workspace.py         # 🚧 Workspace/Node/Rule + WorkspaceManager (rule engine is primitive)
│       │   └── 📁 gateway/         # ✅ server-runtime building blocks (extensible)
│       │       ├── 📄 bus.py           # async pub/sub MessageBus
│       │       ├── 📄 events.py        # InboundMessage / OutboundMessage
│       │       ├── 📄 channel.py       # BaseChannel (abstract) + ChannelManager
│       │       ├── 📄 session.py       # Session / SessionManager (JSONL)
│       │       ├── 📄 services.py      # CronService / CronJob / CronSchedule
│       │       └── 📄 orchestrator.py  # GatewayOrchestrator / Lifecycle / Phase
│       │
│       ├── 📁 data/               # Data management
│       │   └── 📁 local/          # ✅ LocalDataManager
│       │       ├── 📄 manager.py       # facade
│       │       ├── 📄 storage.py       # hash-based content store (dedup)
│       │       ├── 📄 index.py         # master index of FileMetadata
│       │       ├── 📄 transaction_log.py # append-only audit trail
│       │       └── 📄 file_handlers.py # text / markdown / csv handlers
│       │
│       ├── 📁 memory/             # ✅ Memory backends
│       │   ├── 📄 base_memory.py       # BaseMemory ABC
│       │   ├── 📄 sqlite.py            # SQLiteMemory (sqlite-vec + fastembed)
│       │   ├── 📄 md_store.py          # MEMORY.md / HISTORY.md helpers
│       │   ├── 📄 distiller.py         # MemoryDistiller (3-tier promotion)
│       │   ├── 📄 llm_filter.py        # create_llm_filter (LLM extractor)
│       │   └── 📄 types.py             # MemoryEntry, MemoryQueryResult
│       │
│       ├── 📁 session/            # ✅ JsonlSessionStore (chat transcripts)
│       │   └── 📄 store.py
│       │
│       ├── 📁 task/               # ✅ Task runtime
│       │   ├── 📄 control.py           # TaskRuntime (asyncio.TaskGroup)
│       │   ├── 📄 model.py             # Task, AgentTask, TaskInput/Output, enums
│       │   └── 📄 view.py              # 📦 placeholder (no symbols yet)
│       │
│       ├── 📁 tools/              # ✅ Generic tool system
│       │   ├── 📄 __init__.py          # GenericTool, create_tool, @tool, ToolSchema (dataclass)
│       │   ├── 📄 mcp_adapter.py       # MCPToolAdapter, MCPTool
│       │   └── 📄 schemas.py           # pydantic ToolDefinition / ToolExecutionResult / enums
│       │
│       ├── 📁 user/               # User module
│       │   ├── 📄 model.py             # ✅ User dataclass
│       │   └── 📄 controller.py        # 📦 stubbed (every method raises NotImplementedError)
│       │
│       ├── 📁 utils/              # ✅ Utilities
│       │   ├── 📄 chunker.py           # TextChunker (RAG ingestion)
│       │   ├── 📄 gen.py               # Faker-backed name/description generators
│       │   └── 📄 session.py           # append_transcript test/seed helper
│       │
│       ├── 📁 workflow/           # ✅ Workflow tracing models
│       │   ├── 📄 models.py            # WorkflowTrace, WorkflowRun, records (__init__ is empty)
│       │   └── 📄 controller.py        # WorkflowController
│       │
│       └── 📁 workspace_fs/       # ✅ On-disk workspace layer
│           ├── 📄 layout.py            # WorkspaceLayout, BOOTSTRAP_PROMPT_FILES
│           ├── 📄 bootstrap.py         # init_workspace (scaffolds templates)
│           └── 📄 reader.py            # read_prompt_files, read_memory_md, list_skills
│
├── 📁 examples/                   # Usage examples
│   ├── 📄 minion_agent_example.py
│   ├── 📄 sqlite_memory_example.py
│   ├── 📄 tasks_example.py
│   ├── 📄 document_ingestion_example.py
│   └── 📁 example_chat/                # a seeded workspace + chat_example.py
│
└── 📁 tests/                      # Test suite (pytest, asyncio_mode=auto)
    ├── 📄 conftest.py
    ├── 📄 test_bootstrap.py
    ├── 📄 test_execution.py
    ├── 📁 unit/                        # agent, mcp_adapter, task model/runtime
    ├── 📁 integration/                 # cli, context, distiller, gateway, memory, sessions
    ├── 📁 e2e/                         # end-to-end CLI + data management
    └── 📁 workflow/                    # workflow controller/models
```

## Module Status Legend

- ✅ **Complete** — implemented and functional
- 🚧 **Partial** — works, but with known gaps (see notes)
- 📦 **Provisioned** — stubbed/placeholder only

## Notes on partial / provisioned modules

- **`cli/workflow.py`** — the command group is fully written but its registration
  is commented out in `cli/main.py`, so `miminions workflow ...` is unreachable.
- **`core/workspace.py`** — the `Workspace`/`Node`/`Rule` model and JSON-backed
  `WorkspaceManager` work; the rule **condition engine is primitive** (basic
  state matching), so `evaluate_state_logic` is intentionally simple.
- **`core/gateway/`** — complete as a runtime **toolkit**: `BaseChannel` and
  `GatewayOrchestrator` are abstract extension points and **no concrete channels
  ship built-in**. Cron-expression schedules need the optional `croniter` package.
- **`task/view.py`** — module docstring only; no view functions yet.
- **`user/controller.py`** — fully stubbed; every method (including `__init__`)
  raises `NotImplementedError`. The `User` dataclass model is functional.
- **`agent run --async`** — accepts the flag but is a no-op placeholder.

## Public Import Surface

> ⚠️ The top-level `from miminions import ...` is currently broken (the package
> `__init__` swallows an `ImportError`). Always import from the concrete
> subpackages below.

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

## Key Dependencies

**Core** (installed by `pip install miminions`): `pydantic`, `pydantic-ai`,
`openai`, `mcp`, `click`, `numpy`, `pdfplumber`, `Faker`.

**`[sqlite]` / `[all]` extra** (vector memory): `fastembed` (ONNX embeddings,
no PyTorch/CUDA), `sqlite-vec`, `pysqlite3`.

**Optional**: `croniter` (gateway cron-expression schedules), `pyinstaller`
(`[cli-build]` standalone binary).
