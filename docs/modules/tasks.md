# Tasks & Workflows

This page covers two related runtime layers:

- **Tasks** (`miminions.task`) — bind a [Minion](agent.md) to a unit of work and run many of them **concurrently** with `asyncio.TaskGroup`.
- **Workflow tracing** (`miminions.workflow`) — small, serializable records that capture what an agent did (its turns and tool calls), persisted by the [`miminions execution`](cli.md#execution) CLI.

!!! note "Import from the subpackages"
    The top-level `import miminions` re-exports nothing. Import tasks from `miminions.task`, and workflow trace models from their submodules (`miminions.workflow` has **no** package-level exports).

    ```python
    from miminions.task import TaskRuntime, Task, AgentTask, TaskStatus, TaskPriority
    from miminions.task.model import TaskInput, TaskOutput
    from miminions.workflow.models import WorkflowTrace, WorkflowRun, ToolCallRecord, AgentRunRecord
    from miminions.workflow.controller import WorkflowController
    ```

---

## Part 1 — Tasks

A **`Task`** is a dataclass describing a unit of work (id, name, description, status, priority, timing). An **`AgentTask`** extends it by binding an [agent](agent.md) plus the `args`/`kwargs` to pass to that agent's `run()`. The **`TaskRuntime`** collects `AgentTask`s and executes them concurrently.

!!! info "Python 3.12+"
    `TaskRuntime.run()` uses `asyncio.TaskGroup`, which requires Python **3.11+** — already satisfied by MiMinions' `>= 3.12` floor.

### Quick Start

```python
import asyncio
from miminions.agent import create_minion
from miminions.task import TaskRuntime, AgentTask

async def main():
    runtime = TaskRuntime()

    # Bind agents to tasks. Each AgentTask.agent must expose an async run().
    # create_minion(...) returns a Minion, which does.
    runtime.add_task(AgentTask(
        name="haiku",
        agent=create_minion("Poet", provider="test"),
        args=["Write a haiku about minions."],
    ))
    runtime.add_task(AgentTask(
        name="summary",
        agent=create_minion("Summarizer", provider="test"),
        args=["Summarize what an agentic framework is."],
    ))

    # Runs every task concurrently in one TaskGroup.
    results = await runtime.run()

    # The dict is keyed by task.id (a uuid1), not by the name you set.
    for task_id, info in results.items():
        print(task_id, info["status"], info["result"])

asyncio.run(main())
```

`run()` returns a dict keyed by `task.id` (the random `uuid1` id, **not** the `name` you set); each value is `{"status": TaskStatus, "result": <agent output>}`. Both fields are also written back onto the stored `AgentTask` (`.status`, `.result`). To recover a task's `name` from its id, look it up via `runtime.get_tasks()[task_id].name`.

!!! note "In-code docstring is inaccurate"
    `TaskRuntime.run()`'s own docstring says it returns "task names as keys" — that wording is wrong. The code builds the dict from `self.tasks.items()`, which is keyed by `task.id`.

!!! tip "Synchronous entry point"
    From non-async code, call `runtime.run_sync()`. It spins up a fresh event loop, runs `run()`, and returns the same result dict.

### `AgentTask` fields

`AgentTask` is a `@dataclass` extending `Task`. Sensible defaults mean you usually only set `agent` and `args`.

| Field | Type | Default | Notes |
| --- | --- | --- | --- |
| `id` | `str` | random `uuid1()` | Unique task id; used as the key in `TaskRuntime.tasks`. |
| `name` | `str` | random name | Human-readable label only — **not** the key in the results dict (the `id` is). |
| `description` | `str` | random sentence | Free-text description. |
| `status` | `TaskStatus` | `PENDING` | Updated by the runtime as the task progresses. |
| `priority` | `TaskPriority` | `MEDIUM` | Advisory priority level (see below). |
| `start_time` / `end_time` | `datetime \| None` | `None` | Not auto-populated by the runtime. |
| `agent` | `Agent` | `None` | The bound agent. Must expose an awaitable `run()`. |
| `args` | `list` | `[]` | Positional args forwarded to `agent.run(*args, ...)`. |
| `kwargs` | `dict` | `{}` | Keyword args forwarded to `agent.run(..., **kwargs)`. |
| `max_turns` | `int` | `5` | **Not currently applied** — see limitations. |
| `call_back` | `callable \| None` | `None` | Stored on the task; not invoked by the current runtime. |
| `result` | `AgentRunResult` | `None` | Populated with the agent's output after `run()`. |

### Status & priority

=== "`TaskStatus`"

    | Value | Meaning |
    | --- | --- |
    | `PENDING` | Created, waiting. |
    | `INITIALIZED` | Runtime initialized. |
    | `IDLE` | Ready to execute. |
    | `RUNNING` | Currently executing. |
    | `IN_PROGRESS` | Alias kept for CLI compatibility. |
    | `PAUSED` | Execution paused. |
    | `COMPLETED` | Finished successfully. |
    | `FAILED` | Raised an exception during the run. |
    | `CANCELLED` | Cancelled. |

=== "`TaskPriority`"

    | Value |
    | --- |
    | `LOW` |
    | `MEDIUM` |
    | `HIGH` |
    | `CRITICAL` |

### Managing the task set

`TaskRuntime` keeps tasks in a dict keyed by `task.id`.

```python
runtime = TaskRuntime()
task = AgentTask(name="job", agent=create_minion("A", provider="test"), args=["hi"])
runtime.add_task(task)

runtime.get_tasks()                          # -> {task.id: AgentTask, ...}
runtime.filter_tasks("status", TaskStatus.PENDING)   # -> list of matching tasks
runtime.update_task(task.id, priority=TaskPriority.HIGH)
await runtime.get_task_status(task.id)       # -> TaskStatus (or {id: status} if no id given)
runtime.clear_tasks()
```

!!! warning "Limitations — read before relying on this"
    - **Failures are swallowed.** When a bound agent raises, the task's status is set to `TaskStatus.FAILED`, but the exception itself is **not** re-raised or surfaced in the result dict (`result` stays whatever it was, usually `None`). Inspect `status == TaskStatus.FAILED` to detect failures; the underlying error is not reported.
    - **`max_turns` is not enforced.** `AgentTask.max_turns` is stored but the current runtime does not pass it to the agent or cap turns.
    - **`call_back` is not invoked.** It is stored on the task but the runtime never calls it.
    - **No per-task timing.** `start_time` / `end_time` are not auto-populated.

---

## Part 2 — Workflow tracing

The `miminions.workflow` models are lightweight, JSON-serializable records that describe **what an agent run did**: each agent turn and each tool call, in order. They are the schema behind the [`miminions execution`](cli.md#execution) interaction log.

!!! note "No package-level exports"
    `import miminions.workflow` exposes nothing. Import the concrete symbols from the submodules:

    ```python
    from miminions.workflow.models import (
        WorkflowTrace, WorkflowRun, AgentRunRecord, ToolCallRecord,
    )
    from miminions.workflow.controller import WorkflowController
    ```

### The records

| Type | Captures |
| --- | --- |
| `AgentRunRecord` | One agent turn — `prompt` in, `output` out (plus `id`, `created_at`). |
| `ToolCallRecord` | One tool invocation — `tool_name`, `args`, `kwargs`, `result`, `error`, `status`, `execution_time_ms`, `order`, `timestamp`. |
| `WorkflowTrace` | An **ordered** list of agent and tool records — the single source of truth for sequence. |
| `WorkflowRun` | A completed run: `agent_name` + a `WorkflowTrace` (plus `id`, `created_at`, `schema_version`). |

Every record has `to_dict()` / `from_dict()` for round-tripping to JSON.

### Building a trace by hand

```python
from miminions.workflow.models import WorkflowTrace, WorkflowRun, AgentRunRecord

trace = WorkflowTrace()
trace.add_agent_record(AgentRunRecord(prompt="Add 2 and 3", output="5"))
trace.add_tool_record(
    tool_name="add",
    kwargs={"a": 2, "b": 3},
    result=5,
    status="success",
    execution_time_ms=0.4,
)

# Aggregate helpers
print(trace.tool_usage_counts())  # {'add': 1}
print(trace.most_used_tool())     # 'add'

run = WorkflowRun(agent_name="Calculator", trace=trace)
serialized = run.to_dict()                 # JSON-ready dict
restored = WorkflowRun.from_dict(serialized)
```

### `WorkflowController` — trace a Minion's tool calls

`WorkflowController` bridges a [Minion](agent.md) and a trace. You create the `AgentRunRecord` and `WorkflowTrace`, hand them to the controller, and every `execute(...)` it proxies to the agent is recorded into the trace automatically.

```python
from miminions.agent import create_minion
from miminions.workflow.models import AgentRunRecord, WorkflowTrace
from miminions.workflow.controller import WorkflowController

agent = create_minion("Calculator", provider="test")
agent.register_tool("add", "Add two numbers", lambda a, b: a + b)

record = AgentRunRecord(prompt="Add 6 and 7")
trace = WorkflowTrace()
controller = WorkflowController(agent, agent_record=record, trace=trace)

# Proxies to agent.execute(...) and appends a ToolCallRecord to the trace
result = controller.execute("add", arguments={"a": 6, "b": 7})

run = controller.finish_run(output="13")   # -> WorkflowRun
```

!!! note
    The controller only **appends** records — it never starts a run on its own. It uses the agent's `execute` / `execute_async` (which return `ToolExecutionResult` and never raise), so a failing tool is recorded with an `error` and `status` rather than crashing the trace. There is also an async `await controller.execute_async(...)`.

---

## How workflows are driven today

!!! note
    MiMinions does not ship a `miminions workflow` command. Workflow orchestration is exposed through Python APIs and execution traces instead of a dedicated CLI group.

In the current release, workflow orchestration is driven through:

1. **The `TaskRuntime` API** (above) for running agent-bound work concurrently in Python.
2. **The [`miminions execution`](cli.md#execution) commands**, which persist each tool run as a `WorkflowRun` (`AgentRunRecord` + `ToolCallRecord`) under `~/.miminions/interactions.json`. `execution interaction list` / `show` read those traces back.

So the trace models on this page are real and in use — just consumed via `execution` and `TaskRuntime`, not a shipped workflow command group.

---

## API Reference

### `TaskRuntime`

| Method | Description |
| --- | --- |
| `add_task(task: AgentTask)` | Add a task (keyed by `task.id`). |
| `get_tasks() -> dict[str, AgentTask]` | All tasks by id. |
| `filter_tasks(attribute, value) -> list` | Tasks whose attribute equals `value`. |
| `update_task(task_id, **attrs)` | Set attributes on a task; raises `ValueError` if id missing. |
| `clear_tasks()` | Remove all tasks. |
| `async run() -> dict` | Run all tasks concurrently; returns `{task_id: {"status", "result"}}` (keyed by `task.id`). |
| `run_sync() -> dict` | Synchronous wrapper around `run()` (manages its own event loop). |
| `async get_task_status(task_id=None) -> TaskStatus` | One task's status, or `{id: status}` for all when `task_id` is `None`. |

### `WorkflowTrace`

| Method | Description |
| --- | --- |
| `add_agent_record(record)` | Append an `AgentRunRecord`. |
| `add_tool_record(tool_name, *, args=None, kwargs=None, result=None, error=None, status=None, execution_time_ms=None) -> ToolCallRecord` | Append a tool call and return it. |
| `tool_usage_counts() -> dict[str, int]` | Count of calls per tool. |
| `most_used_tool() -> str \| None` | Most-called tool, or `None`. |
| `to_dict()` / `from_dict(data)` | JSON round-trip. |

### `WorkflowController`

| Method | Description |
| --- | --- |
| `WorkflowController(agent, agent_record, trace, agent_name=None)` | Bind an agent + record + trace; the record is appended to the trace. |
| `execute(tool_name, arguments=None, **kwargs) -> ToolExecutionResult` | Proxy to `agent.execute` and record the call. |
| `async execute_async(tool_name, arguments=None, **kwargs)` | Async variant. |
| `finish_run(output) -> WorkflowRun` | Set the agent record's output and return a `WorkflowRun`. |

## See Also

<div class="grid cards" markdown>

- :material-robot: **[Agent](agent.md)** — the `Minion` each `AgentTask` binds to
- :material-console: **[CLI & Chat](cli.md)** — the `execution` commands that persist `WorkflowRun`s
- :material-graph: **[Workspaces](workspaces.md)** — nodes, rules, and on-disk layout

</div>
