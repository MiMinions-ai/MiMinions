# MiMinions Repository Structure

```
MiMinions/
├── 📄 README.md                    # Project documentation and quick start
├── 📄 CHANGELOG.md                 # Version history
├── 📄 CONTRIBUTING.md              # Contribution guidelines
├── 📄 CODE_OF_CONDUCT.md           # Community standards
├── 📄 LICENSE                      # License file
├── 📄 pyproject.toml               # Project configuration & dependencies
├── 📄 setup.py                     # Package setup
├── 📄 setup.cfg                    # Setup configuration
├── 📄 requirements.txt             # Dependencies
├── 📄 MANIFEST.in                  # Package manifest
├── 📄 main.py                      # Entry point
├── 📓 work_bench.ipynb             # Development notebook
│
├── 📁 src/
│   └── 📁 miminions/               # Main package
│       ├── 📄 __init__.py          # Package exports
│       │
│       ├── 📁 agent/               # Agent implementations
│       │   ├── 📄 __init__.py
│       │   ├── 📄 base.py          # Base agent (provisioned)
│       │   ├── 📄 simple_agent.py  # ✅ Enhanced agent with MCP & memory
│       │   ├── 📄 README.md
│       │   └── 📄 QUICKSTART.md
│       │
│       ├── 📁 core/                # Core workspace system
│       │   ├── 📄 __init__.py
│       │   ├── 📄 workspace.py     # 🚧 Workspace, Node, Rule management
│       │   └── 📄 README.md
│       │
│       ├── 📁 data/                # Data management
│       │   ├── 📄 __init__.py
│       │   ├── 📄 README.md
│       │   └── 📁 local/           # ✅ Local file system management
│       │       ├── 📄 __init__.py
│       │       ├── 📄 manager.py       # Main data manager interface
│       │       ├── 📄 storage.py       # Hash-based storage backend
│       │       ├── 📄 index.py         # Master index for metadata
│       │       ├── 📄 transaction_log.py # Audit trail
│       │       ├── 📄 file_handlers.py # File type handlers
│       │       └── 📄 README.md
│       │
│       ├── 📁 interface/           # User interfaces
│       │   ├── 📄 __init__.py
│       │   ├── 📄 README.md
│       │   └── 📁 cli/             # ✅ Command line interface
│       │       ├── 📄 __init__.py
│       │       ├── 📄 main.py          # CLI entry point
│       │       ├── 📄 auth.py          # Authentication commands
│       │       ├── 📄 agent.py         # Agent management
│       │       ├── 📄 task.py          # Task management
│       │       ├── 📄 workflow.py      # Workflow management
│       │       ├── 📄 knowledge.py     # Knowledge base
│       │       └── 📄 workspace.py     # Workspace commands
│       │
│       ├── 📁 memory/              # ✅ Vector memory backends
│       │   ├── 📄 base_memory.py       # Abstract base class
│       │   ├── 📄 sqlite.py            # SQLite + sqlite-vec
│       │   └── 📄 md_store.py          # Markdown-backed storage helpers
│       │
│       ├── 📁 tools/               # ✅ Generic tool system
│       │   ├── 📄 __init__.py          # GenericTool, SimpleTool, decorators
│       │   ├── 📄 mcp_adapter.py       # MCP server integration
│       │   └── 📄 README.md
│       │
│       ├── 📁 user/                # User management
│       │   ├── 📄 __init__.py
│       │   ├── 📄 model.py             # ✅ User dataclass
│       │   ├── 📄 controller.py        # 📦 Stubbed (not implemented)
│       │   └── 📄 README.md
│       │
│       └── 📁 utils/               # ✅ Utilities
│           ├── 📄 __init__.py
│           └── 📄 chunker.py           # Text chunking for documents
│
├── 📁 examples/                    # Usage examples
│   ├── 📄 __init__.py
│   ├── 📄 README.md
│   ├── 📄 simple_agent_example.py      # Basic agent usage
│   ├── 📄 agent_memory_example.py      # Agent with memory
│   ├── 📄 document_ingestion_example.py
│   ├── 📄 document_server_example.py
│   ├── 📄 sqlite_memory_example.py
│   ├── 📄 sqlite_memory_search_example.py
│   ├── 📁 example_files/               # Sample files for examples
│   ├── 📁 servers/                     # MCP server examples
│   │   ├── 📄 document_server.py
│   │   └── 📄 math_server.py
│   └── 📁 legacy/                      # Older examples
│       ├── 📄 README.md
│       ├── 📄 cli_demo.py
│       ├── 📄 custom_tools_example.py
│       ├── 📄 database_integration_example.py
│       ├── 📄 demo.py
│       ├── 📄 memory_management_example.py
│       └── 📁 data_management/
│
└── 📁 tests/                       # Test suite
    ├── 📄 __init__.py
    ├── 📄 conftest.py                  # Pytest fixtures
    ├── 📄 test_memory.py
    ├── 📄 test_simple_agent.py
    ├── 📄 test_sqlite_memory.py
    ├── 📄 test_sqlite_memory_search.py
    ├── 📄 document_test.py
    ├── 📁 cli/                         # CLI tests
    │   ├── 📄 __init__.py
    │   ├── 📄 test_agent.py
    │   ├── 📄 test_auth.py
    │   ├── 📄 test_e2e.py
    │   ├── 📄 test_runner.py
    │   └── 📄 test_workspace.py
    └── 📁 data/                        # Data management tests
        ├── 📄 __init__.py
        ├── 📄 test_data_management.py
        └── 📄 test_data_management_e2e.py
```

## Module Status Legend

- ✅ **Complete** - Fully implemented and functional
- 🚧 **In Progress** - Partially implemented
- 📦 **Provisioned** - Stubbed/placeholder only

---

## ✅ Complete Modules

- **Tools System** (`src/miminions/tools/`) - Generic tool abstraction with `GenericTool`, `SimpleTool`, schema extraction, and framework-agnostic design
- **MCP Adapter** (`src/miminions/tools/mcp_adapter.py`) - Full MCP server integration - connect, load tools, execute, and convert to generic format
- **Simple Agent** (`src/miminions/agent/simple_agent.py`) - Enhanced agent with MCP support, memory integration, document ingestion, and auto-registered CRUD tools
- **SQLite Memory** (`src/miminions/memory/sqlite.py`) - Vector-based memory using `sqlite-vec` with CRUD, keyword search, regex, and full-text search
- **Base Memory** (`src/miminions/memory/base_memory.py`) - Abstract base class defining memory interface
- **Text Chunker** (`src/miminions/utils/chunker.py`) - Document chunking utility with configurable overlap
- **Local Data Manager** (`src/miminions/data/local/`) - Full file management with master index, transaction logs, hash-based storage, and file handlers
- **CLI - Auth** (`src/miminions/interface/cli/auth.py`) - Authentication with signin, signout, config management, public access mode
- **CLI - Agent** (`src/miminions/interface/cli/agent.py`) - Agent management (list, add, update, remove, set-goal, activate, deactivate)
- **CLI - Task** (`src/miminions/interface/cli/task.py`) - Task management with full CRUD and status tracking
- **CLI - Workflow** (`src/miminions/interface/cli/workflow.py`) - Workflow management with agent assignment
- **CLI - Knowledge** (`src/miminions/interface/cli/knowledge.py`) - Knowledge base CRUD with categories and versioning
- **User Model** (`src/miminions/user/model.py`) - User dataclass with serialization

## 🚧 In Progress Modules

- **Core Workspace** (`src/miminions/core/workspace.py`) - ~70% complete - Has `Node`, `Rule`, `Workspace` dataclasses, `WorkspaceManager` with persistence. Rule evaluation and state logic need finishing
- **CLI - Workspace** (`src/miminions/interface/cli/workspace.py`) - ~80% complete - Commands exist but rely on incomplete workspace logic
- **Base Agent** (`src/miminions/agent/base.py`) - Minimal - only imports `pydantic_ai.Agent`, database integration mentioned in README but not implemented

## 📦 Provisioned / Stubbed Modules

- **User Controller** (`src/miminions/user/controller.py`) - Fully stubbed - All methods raise `NotImplementedError` (CRUD, API key generation/validation)

## 🔬 Test Coverage

- **Memory** - `test_memory.py`, `test_sqlite_memory.py`, `test_sqlite_memory_search.py` - Good coverage
- **Agent** - `test_simple_agent.py` - Basic coverage
- **CLI** - `tests/cli/` - Has auth, agent, workspace, and e2e tests
- **Data** - `tests/data/` - Data management e2e tests

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         CLI Interface                           │
│  (auth, agent, task, workflow, knowledge, workspace commands)   │
└─────────────────────────────┬───────────────────────────────────┘
                              │
┌─────────────────────────────▼───────────────────────────────────┐
│                        Simple Agent                             │
│         (MCP integration, tool execution, memory CRUD)          │
└──────────┬──────────────────┬───────────────────┬───────────────┘
           │                  │                   │
┌──────────▼──────┐  ┌────────▼────────┐  ┌──────▼──────────┐
│   Tools System  │  │  Memory System  │  │  Data Manager   │
│  ┌───────────┐  │  │  ┌──────────┐   │  │  ┌──────────┐   │
│  │ Generic   │  │  │  │ SQLite   │   │  │  │ Storage  │   │
│  │ Tool      │  │  │  │ Memory   │   │  │  │ Backend  │   │
│  └───────────┘  │  │  └──────────┘   │  │  └──────────┘   │
│  ┌───────────┐  │  │  ┌──────────┐   │  │  ┌──────────┐   │
│  │ MCP       │  │  │  │ SQLite   │   │  │  │ Index    │   │
│  │ Adapter   │  │  │  │ Memory   │   │  │  └──────────┘   │
│  └───────────┘  │  │  └──────────┘   │  │  ┌──────────┐   │
└─────────────────┘  └─────────────────┘  │  │ Tx Log   │   │
                                          │  └──────────┘   │
┌─────────────────┐  ┌─────────────────┐  └─────────────────┘
│  Core Workspace │  │  User Module    │
│  ┌───────────┐  │  │  ┌──────────┐   │
│  │ Nodes     │  │  │  │ Model ✅ │   │
│  └───────────┘  │  │  └──────────┘   │
│  ┌───────────┐  │  │  ┌──────────┐   │
│  │ Rules     │  │  │  │Controller│   │
│  └───────────┘  │  │  │   📦     │   │
└─────────────────┘  │  └──────────┘   │
                     └─────────────────┘
```

## Key Dependencies

- **mcp** - Model Context Protocol client
- **fastmcp** - Fast MCP utilities
- **fastembed** - Text embeddings (ONNX, no PyTorch/CUDA)
- **sqlite-vec** - SQLite vector extension
- **pdfplumber** - PDF text extraction
- **click** - CLI framework
- **pydantic-ai** - AI agent framework
