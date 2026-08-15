# MiMinions Tests

Comprehensive test suites for the Minion Agent.

## Test Tiers

| Tier | Folder | Scope | Speed |
|---|---|---|---|
| **unit** | `tests/unit/` | Package logic only — no external services or filesystem I/O | < 5s |
| **integration** | `tests/integration/` | Filesystem and external services (CLI, gateway, SQLite, session store) | Seconds–minutes |
| **e2e** | `tests/e2e/` | Complete use-case flows from the CLI | Minutes |

## Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# End-to-end tests
pytest tests/e2e -v

# Full suite
pytest tests/ -v

# Advisory coverage for CLI/workspace modules.
# First install dev test tooling:
#   python -m pip install -e ".[dev]"
python -m coverage run --source=miminions.cli,miminions.core.workspace,miminions.workspace_fs -m pytest tests/unit tests/integration
python -m coverage report -m --omit="*/miminions/cli/workflow.py"
```

## Test Files

### unit/
- **test_agent.py** — Agent creation, tool registration, structured result validation
- **test_mcp_adapter.py** — MCP adapter logic
- **test_task_model.py** — Task model enums and dataclasses
- **test_task_runtime.py** — Task runtime logic

### integration/
- **test_context_builder.py** — ContextBuilder memory injection
- **test_distiller.py** — MemoryDistiller session distillation pipeline
- **test_document_ingestion.py** — PDF/text ingestion and chunking
- **test_md_store.py** — Markdown memory store read/write
- **test_session_store.py** — JSONL session persistence
- **test_sqlite_memory.py** — SQLite vector memory CRUD
- **test_cli_agent.py** — CLI agent command
- **test_cli_auth.py** — CLI auth flow
- **test_cli_chat.py** — CLI chat session
- **test_cli_runner.py** — CLI runner
- **test_cli_workspace.py** — CLI workspace commands
- **test_cli_workspace_init_files.py** — Workspace file initialisation
- **test_data_management.py** — Data management system
- **test_gateway_bus.py** — Gateway event bus
- **test_gateway_channel.py** — Gateway channels
- **test_gateway_events.py** — Gateway event model
- **test_gateway_orchestrator.py** — Gateway orchestrator
- **test_gateway_services.py** — Gateway services
- **test_gateway_session.py** — Gateway session handling

### e2e/
- **test_e2e.py** — Full CLI use-case flows
- **test_data_management_e2e.py** — Data management end-to-end
