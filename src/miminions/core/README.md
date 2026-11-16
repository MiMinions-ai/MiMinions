# MiMinions Core

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).
> Contract version: 1. See the [package map and vocabulary](../../../STRUCTURE.md#package-ownership).

## Purpose

`miminions.core` groups agent behavior, tool contracts, prompt and memory
processing, in-memory tasks, and workspace models. It is not a pure, IO-free
domain layer: workspace persistence and context loading already perform IO.

| Module | Responsibility |
|--------|----------------|
| [agent/](agent/README.md) | `Minion`, model/provider selection, tool registration, MCP connections and the reasoning loop. |
| [agent/memory/](agent/memory/README.md) | Memory backend contracts and types; re-exports memory-processing and Markdown helpers implemented elsewhere. |
| [context/](context/README.md) | System-prompt assembly, section budgets, memory distillation and compaction. |
| [task/](task/README.md) | Task models and `TaskRuntime` for execution inside one process. |
| [tool/](tool/README.md) | Generic callable/schema adapters, MCP integration and approved project-function tools. |
| [workspace/](workspace/README.md) | Workspace graph and JSON registry, filesystem layout, bootstrap templates, readers and project discovery. |
| [paths.py](paths.py), [persistence.py](persistence.py) | Config-home path resolution and shared JSON persistence. |
| [knowledge/](knowledge/) | Empty reserved package, not the implementation of the knowledge CLI. |

First-run application setup belongs to [interface/bootstrap.py](../interface/bootstrap.py),
not workspace template bootstrapping. CLI commands belong to
[interface/](../interface/README.md); durable execution and storage adapters to
[system/](../system/README.md); gateway services to [daemon/](../daemon/README.md).

## Public surface

Import domain APIs from their subpackages:

```python
from miminions.core.workspace import WorkspaceManager, resolve_workspace
from miminions.core.agent import Minion, create_minion
from miminions.core.context import ContextBuilder
from miminions.core.task import TaskRuntime
from miminions.core.tool import GenericTool
```

The package root currently re-exports gateway symbols only: `BaseChannel`,
`ChannelManager`, `CronJob`, `CronSchedule`, `CronService`, `GatewayOrchestrator`,
`InboundMessage`, `Lifecycle`, `MessageBus`, `OutboundMessage`, `Phase`,
`Session`, and `SessionManager`. Their implementation owner is still `daemon`;
the re-export does not move gateway responsibilities into `core`.

## State

Agents and `TaskRuntime` hold process-local state. `WorkspaceManager` persists
workspace records in `workspaces.json` (`WORKSPACE_SCHEMA_VERSION = 1`).
Workspace files and memory-processing state are described in the workspace and
context contracts; they are not all in-memory merely because they live in `core`.

## Lifecycle

Callers construct agents and runtimes, resolve or create workspaces, and attach
context/tools explicitly. Workspace template initialization is idempotent.
The workspace rule engine intentionally supports only basic state matching.

## Gate

Run `python scripts/check_structure.py` for package contracts. Focused examples:
`python -m pytest tests/unit/core tests/unit/test_core_workspace.py` and
`python -m pytest tests/integration/context`. Other subpackages list their own gates.
