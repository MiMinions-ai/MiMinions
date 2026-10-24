# Workflow (Trace Models & Controller) — Internal

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).
> **Internal module: no public surface.** `__init__.py` is intentionally empty.

## Purpose

Record what an agent run did — tool calls, agent records, full traces —
so runs can be inspected after the fact. Owns trace data structures and
the append-only bridge from the agent; never starts runs on its own and
never owns task execution (see `task` / `execution`).

## Public surface

None. Import from submodules only, inside the package:

```python
from miminions.workflow.models import AgentRunRecord, WorkflowRun, WorkflowTrace, ToolCallRecord
from miminions.workflow.controller import WorkflowController
```

Promoting any symbol to `__init__.py` is a contract change: declare the
surface here, bump the version, and update the registry in the spec.

## State

Caller-owned `WorkflowTrace` / `AgentRunRecord` dataclasses (ISO-8601
timestamps, per-call `status`, `error`, `execution_time_ms`). The
controller only appends records the caller created.

## Lifecycle

Caller creates record + trace → `WorkflowController(agent, record, trace)`
appends on `execute()` → `finish_run(output)` seals the `WorkflowRun`.

## Gate

Workflow tests plus `scripts/check_structure.py` (which asserts this
module stays surface-less until declared). Contract version: 1.
