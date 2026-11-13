# MiMinions System Services

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).
> Contract version: 1. See the [package map and vocabulary](../../../STRUCTURE.md#package-ownership).

## Purpose

`miminions.system` groups storage implementations, durable local execution,
and authentication compatibility helpers. It is not just the content-addressable
data manager, and not every module here is a generic infrastructure adapter.

| Module | Responsibility |
|--------|----------------|
| [execution/](execution/README.md) | Persistent task queue, worker/supervisor, events, approvals, checkpoints and task handlers. |
| [file/](file/README.md) | Content-addressable files, metadata index and transaction log; separate Markdown memory IO helpers. |
| [db/sqlite.py](db/sqlite.py) | `SQLiteMemory`, the embedding/vector memory backend, requiring the `sqlite` extra. |
| [auth/auth.py](auth/auth.py) | Local-auth compatibility helpers. `require_auth` currently leaves commands unblocked; it is not an enforced sign-in boundary. |
| [config/](config/) | Empty reserved package. Current configuration helpers live in `interface.config` and `core.paths`. |

Agent reasoning remains in [core/agent](../core/agent/README.md); memory extraction
and compaction policies are in [core/context](../core/context/README.md).
Execution handlers orchestrate those capabilities and currently call some
CLI-private helpers. The auth module also imports CLI auth helpers.
These are existing dependencies, not an enforced clean-layer architecture.

## Public surface

The root re-exports `LocalDataManager` only. Other APIs have explicit subpackage
imports:

```python
from miminions.system import LocalDataManager
from miminions.system.db.sqlite import SQLiteMemory
from miminions.system.execution import ExecutionService, ExecutionRequest
```

## State

- Durable execution owns `<config_home>/execution.sqlite3`: tasks, events,
  approvals and model-message checkpoints.
- `LocalDataManager` owns content-addressed files, an index and transaction logs
  under its `base_dir`. Its default is `~/.miminions/`; pass an explicit path when
  using a different home.
- `SQLiteMemory` owns its configured database. The global-memory pipeline passes
  the global-memory path; the standalone backend has its own default.
- Markdown helpers operate on a supplied workspace root. They are separate from
  the content-addressable data manager.

Do not confuse the execution SQLite database with vector-memory SQLite databases.

## Lifecycle

The execution service queues requests and manages workers; handlers record events
and terminal outcomes. File and database adapters perform storage operations when
called. Constructing a store may create directories, files or database tables;
these APIs are not pure transformations.

## Gate

Focused examples:
`python -m pytest tests/unit/test_execution_dispatch.py tests/integration/test_execution_processes.py`,
`python -m pytest tests/integration/data tests/e2e/test_data_management_e2e.py`,
and `python -m pytest tests/integration/memory/test_sqlite.py` with the `sqlite`
extra installed. Run `python scripts/check_structure.py` for package contracts.
