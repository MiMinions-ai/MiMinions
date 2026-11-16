# Task (In-Memory Task Runtime)

> Contract: [Recursive, Bounded Evolution](../../../../docs/architecture/recursive-evolution.md).
> In-memory only. For durable, cross-process execution use [system.execution](../../system/execution/README.md) — the two must never merge silently.

## Purpose

Model and run agent tasks inside one process: creation, status tracking,
filtering, and async execution. Tracks in-memory task lifecycle status;
never owns persistence or process supervision.

The CLI also calls saved records in `tasks.json` "work items" and queued
`ExecutionTask` records "executions". Neither is this package's process-local
runtime; `miminions task list --kind` distinguishes the two CLI record types.

## Public surface

```python
from miminions.core.task import TaskRuntime, Task, AgentTask, TaskStatus, TaskPriority
# DEFAULT_RUNTIME is a shared process-wide runtime instance.
```

`TaskStatus` includes pending, initialized, idle, running/in_progress, paused,
completed, failed and cancelled; this list is not an enforced transition order.
`TaskPriority`: low/medium/high/critical.

## State

`TaskRuntime.tasks` (in-memory dict) plus `DEFAULT_RUNTIME`. Nothing is
written to disk by this module; if it must survive a restart, it belongs
in `execution`.

## Lifecycle

`add_task()` → `update_task()` transitions → cleared via `clear_tasks()`.
CLI compatibility keeps `in_progress` as an alias of running.

## Gate

Task unit/integration tests plus `scripts/check_structure.py`.
Contract version: 1 (bump on any `TaskStatus`/`TaskPriority` value change).
