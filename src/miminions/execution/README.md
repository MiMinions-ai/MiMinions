# Execution (Durable Local Execution)

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).
> This module is the durable counterpart to the in-memory `task` runtime — never merge the two silently.

## Purpose

Run work in a persistent local instance that survives the calling process:
queued tasks, streamed events, approvals, and checkpoints. Owns durability
and process supervision; never owns agent reasoning or task modelling.

## Public surface

```python
from miminions.execution import (
    ExecutionService, ExecutionRequest, ExecutionTask, TaskEvent, TaskHandle,
)
```

`ExecutionRequest(kind, params, cwd, session_key)` is the serialisable
input; `ExecutionTask` carries `status` with terminal set
`{completed, failed, cancelled}` (`models.TERMINAL`). Trace types
(`WorkflowTrace`, `WorkflowRun`, `AgentRunRecord`, `ToolCallRecord`,
persisted at schema_version 2) live in `execution.trace` — moved here
from the removed `workflow` module, whose only live consumers were
execution handlers and the CLI execution layer. Everything else
(`store`, `worker`, `processes`, `handlers`) is private.

## State

SQLite queue at `<home>/execution.sqlite3` (WAL, `user_version` 1) owned
by `ExecutionStore` — tasks, events, approvals, checkpoints. `<home>`
defaults to the config dir (`core.paths.get_config_dir()`). The DB is the
source of truth for execution state; in-memory handles are views.

## Lifecycle

`ExecutionService` enqueues → supervisor/worker
(`python -m miminions.execution.worker --home <home>`) claims and runs →
handlers emit `phase`/approval events via `TaskContext` → terminal status
is final. Cancellation is cooperative (`cancel_requested`).

## Gate

`pytest tests/unit/test_execution_dispatch.py tests/integration/test_execution_processes.py`
plus `scripts/check_structure.py`. Contract version: 1 (bump on any
`ExecutionRequest`/`ExecutionTask` shape or DB version change, with a
migration note).
