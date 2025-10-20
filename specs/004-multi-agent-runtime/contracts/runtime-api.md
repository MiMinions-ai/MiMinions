# Runtime API Contract

**Feature**: 004-multi-agent-runtime
**Version**: 1.0.0
**Date**: 2025-10-19

## Overview

This document defines the public API contract for the `AgentRuntime` class, which serves as the primary interface for managing multi-agent execution, task queuing, and lifecycle operations.

---

## Class: `AgentRuntime`

Main entry point for the multi-agent runtime system.

### Constructor

```python
class AgentRuntime:
    def __init__(
        self,
        storage_path: str | Path = "~/.miminions/runtime.db",
        resource_limits: ResourceLimit | None = None,
        config: dict | None = None
    ) -> None:
        """
        Initialize a new agent runtime instance.

        Args:
            storage_path: Path to SQLite database for state persistence.
                         Defaults to ~/.miminions/runtime.db
            resource_limits: Resource limit configuration. If None, uses DEFAULT_LIMITS.
            config: Additional runtime configuration options.

        Raises:
            RuntimeError: If storage_path is not writable
            ValueError: If resource_limits are invalid
        """
```

**Configuration Options**:
- `auto_recover`: bool = True - Automatically restart failed agents
- `checkpoint_interval_seconds`: int = 60 - State snapshot frequency
- `enable_metrics`: bool = False - Enable Prometheus metrics (requires [monitoring] extra)
- `log_level`: str = "INFO" - Logging verbosity (DEBUG, INFO, WARNING, ERROR)

---

### Lifecycle Methods

#### `start()`

```python
async def start(self) -> None:
    """
    Start the runtime system.

    Initializes:
    - SQLite database connection and schema
    - Task queue management loop
    - Agent process supervisor
    - IPC message bus
    - Event logging system

    Raises:
        RuntimeError: If runtime already started or initialization fails
        OSError: If cannot create required directories/files

    Post-condition:
        - Runtime status = RUNNING
        - All subsystems operational
        - RUNTIME_STARTED event logged
    """
```

#### `stop()`

```python
async def stop(self, graceful: bool = True, timeout_seconds: int = 30) -> None:
    """
    Stop the runtime system.

    Args:
        graceful: If True, allows running agents to complete current tasks.
                 If False, immediately terminates all agents.
        timeout_seconds: Max time to wait for graceful shutdown before forcing.

    Behavior:
        1. Set runtime status = STOPPING
        2. Pause task queue (no new assignments)
        3. If graceful: Wait for running tasks to complete (up to timeout)
        4. Stop all agents (SIGTERM → 5s → SIGKILL)
        5. Close database connections
        6. Shutdown IPC message bus
        7. Set runtime status = STOPPED

    Post-condition:
        - All agents stopped
        - All resources released
        - Final state saved to database
        - RUNTIME_STOPPED event logged
    """
```

#### `restart()`

```python
async def restart(self) -> None:
    """
    Restart the runtime (convenience wrapper).

    Equivalent to: await stop(graceful=True); await start()

    Raises:
        RuntimeError: If stop() or start() fails
    """
```

---

### Agent Management Methods

#### `register_agent()`

```python
async def register_agent(
    self,
    name: str,
    agent_class: type[BaseAgent] | Callable,
    config: dict | None = None
) -> str:
    """
    Register an agent type with the runtime.

    Args:
        name: Human-readable agent name (unique within runtime)
        agent_class: Agent class (subclass of BaseAgent) or callable
        config: Agent-specific configuration

    Returns:
        agent_id: UUID of registered agent instance

    Raises:
        ValueError: If name already registered or agent_class invalid
        RuntimeError: If runtime not started

    Post-condition:
        - AgentInstance created with status = STOPPED
        - AGENT_REGISTERED event logged
        - Agent not yet running (call start_agent() to execute)
    """
```

#### `start_agent()`

```python
async def start_agent(self, agent_id: str) -> None:
    """
    Start a registered agent in a separate process.

    Args:
        agent_id: UUID of agent to start

    Raises:
        ValueError: If agent_id not found
        RuntimeError: If max_concurrent_agents limit reached
        ProcessError: If agent process fails to start

    Behavior:
        1. Verify resource limits allow new agent
        2. Spawn new process with agent code
        3. Set OS-level resource limits (memory, CPU)
        4. Update agent status = RUNNING
        5. Start heartbeat monitoring

    Post-condition:
        - Agent process running with valid PID
        - Agent status = RUNNING
        - AGENT_STARTED event logged
        - Agent ready to receive task assignments
    """
```

#### `stop_agent()`

```python
async def stop_agent(
    self,
    agent_id: str,
    graceful: bool = True,
    timeout_seconds: int = 5
) -> None:
    """
    Stop a running agent.

    Args:
        agent_id: UUID of agent to stop
        graceful: If True, allow current task to complete
        timeout_seconds: Max wait time for graceful stop

    Raises:
        ValueError: If agent_id not found

    Behavior:
        1. If graceful and agent has active task: wait for completion (up to timeout)
        2. Send SIGTERM to agent process
        3. Wait 5 seconds
        4. If still alive: Send SIGKILL
        5. Update agent status = STOPPED
        6. Release resources

    Post-condition:
        - Agent process terminated
        - Agent status = STOPPED
        - Resources released
        - AGENT_STOPPED event logged
    """
```

#### `pause_agent()`

```python
async def pause_agent(agent_id: str) -> None:
    """
    Pause a running agent (save state, suspend execution).

    Args:
        agent_id: UUID of agent to pause

    Raises:
        ValueError: If agent_id not found or agent not running

    Behavior:
        1. Signal agent to save current state
        2. Wait for state checkpoint completion
        3. Suspend agent process (SIGSTOP)
        4. Update agent status = PAUSED
        5. Release assigned task back to queue

    Post-condition:
        - Agent process suspended (not consuming CPU)
        - Agent state persisted in database
        - Agent status = PAUSED
        - AGENT_PAUSED event logged
        - Can be resumed later with resume_agent()
    """
```

#### `resume_agent()`

```python
async def resume_agent(agent_id: str) -> None:
    """
    Resume a paused agent from saved state.

    Args:
        agent_id: UUID of agent to resume

    Raises:
        ValueError: If agent_id not found or agent not paused

    Behavior:
        1. Resume agent process (SIGCONT)
        2. Restore agent state from database
        3. Update agent status = RUNNING
        4. Re-enable task assignment

    Post-condition:
        - Agent process running
        - Agent continues from paused state
        - Agent status = RUNNING
        - AGENT_RESUMED event logged
    """
```

#### `get_agent_status()`

```python
def get_agent_status(self, agent_id: str) -> AgentInstance:
    """
    Query current agent status and metadata.

    Args:
        agent_id: UUID of agent

    Returns:
        AgentInstance: Current agent state (see data-model.md)

    Raises:
        ValueError: If agent_id not found

    Performance: <10ms (database query)
    """
```

#### `list_agents()`

```python
def list_agents(
    self,
    status: AgentStatus | None = None
) -> list[AgentInstance]:
    """
    List all registered agents, optionally filtered by status.

    Args:
        status: Optional filter (RUNNING, PAUSED, STOPPED, FAILED).
               If None, returns all agents.

    Returns:
        List of AgentInstance objects

    Performance: <50ms for 100 agents
    """
```

---

### Task Management Methods

#### `submit_task()`

```python
async def submit_task(
    self,
    name: str,
    input_data: dict,
    priority: int = 50,
    dependencies: list[str] | None = None,
    timeout_seconds: int | None = None,
    max_retries: int = 0
) -> str:
    """
    Submit a task to the queue for execution.

    Args:
        name: Human-readable task name
        input_data: Task input parameters (must be JSON-serializable)
        priority: Task priority (0=highest, 100=lowest, default=50)
        dependencies: List of task_ids that must complete first (optional)
        timeout_seconds: Max execution time (None = use runtime default)
        max_retries: Number of retry attempts on failure (default: 0)

    Returns:
        task_id: UUID of created task

    Raises:
        ValueError: If dependencies create cycle in task graph
        QueueFullError: If task queue at max capacity
        RuntimeError: If runtime not started

    Post-condition:
        - Task created with status = PENDING
        - Task added to queue (or blocked by dependencies)
        - TASK_ENQUEUED event logged
        - Task will be assigned to next available agent
    """
```

#### `cancel_task()`

```python
async def cancel_task(self, task_id: str) -> bool:
    """
    Cancel a pending or running task.

    Args:
        task_id: UUID of task to cancel

    Returns:
        bool: True if cancelled, False if already completed/failed

    Raises:
        ValueError: If task_id not found

    Behavior:
        - If task status = PENDING: Remove from queue
        - If task status = RUNNING: Signal agent to stop execution
        - If task status = COMPLETED/FAILED/CANCELLED: No-op, return False

    Post-condition:
        - Task status = CANCELLED (if successful)
        - TASK_CANCELLED event logged
        - Agent becomes idle (task_id = null)
    """
```

#### `get_task_status()`

```python
def get_task_status(self, task_id: str) -> Task:
    """
    Query current task status and results.

    Args:
        task_id: UUID of task

    Returns:
        Task: Current task state (see data-model.md)

    Raises:
        ValueError: If task_id not found

    Performance: <10ms (database query)
    """
```

#### `wait_for_task()`

```python
async def wait_for_task(
    self,
    task_id: str,
    timeout_seconds: float | None = None
) -> Task:
    """
    Wait for task completion (async).

    Args:
        task_id: UUID of task to wait for
        timeout_seconds: Max wait time (None = wait forever)

    Returns:
        Task: Completed task with output_data or error_message

    Raises:
        ValueError: If task_id not found
        TimeoutError: If timeout reached before completion

    Behavior:
        - Polls task status every 100ms
        - Returns immediately if task already completed/failed
        - Raises TimeoutError if timeout_seconds exceeded
    """
```

#### `list_tasks()`

```python
def list_tasks(
    self,
    status: TaskStatus | None = None,
    limit: int = 100
) -> list[Task]:
    """
    List tasks, optionally filtered by status.

    Args:
        status: Optional filter (PENDING, RUNNING, COMPLETED, FAILED, CANCELLED)
        limit: Max number of tasks to return (default: 100)

    Returns:
        List of Task objects, ordered by created_at DESC

    Performance: <50ms for 1000 tasks
    """
```

---

### Queue Management Methods

#### `pause_queue()`

```python
async def pause_queue(self) -> None:
    """
    Pause task queue (no new assignments).

    Behavior:
        - Currently running tasks continue
        - No new tasks assigned to idle agents
        - New task submissions still accepted (queued)

    Post-condition:
        - Queue paused = True
        - QUEUE_PAUSED event logged
    """
```

#### `resume_queue()`

```python
async def resume_queue(self) -> None:
    """
    Resume task queue assignments.

    Post-condition:
        - Queue paused = False
        - Idle agents immediately assigned pending tasks
        - QUEUE_RESUMED event logged
    """
```

#### `get_queue_status()`

```python
def get_queue_status(self) -> dict:
    """
    Get current queue statistics.

    Returns:
        dict with keys:
            - pending_count: int - Tasks waiting for assignment
            - running_count: int - Tasks currently executing
            - completed_count: int - Successfully finished tasks
            - failed_count: int - Failed tasks
            - cancelled_count: int - User-cancelled tasks
            - queue_paused: bool - Whether queue is paused
            - max_size: int - Queue capacity limit

    Performance: <10ms
    """
```

---

### Event Log Methods

#### `query_events()`

```python
def query_events(
    self,
    event_type: EventType | None = None,
    agent_id: str | None = None,
    task_id: str | None = None,
    severity: Severity | None = None,
    since: datetime | None = None,
    limit: int = 100
) -> list[EventLog]:
    """
    Query event log with optional filters.

    Args:
        event_type: Filter by event type (optional)
        agent_id: Filter by agent (optional)
        task_id: Filter by task (optional)
        severity: Filter by severity level (optional)
        since: Only return events after this timestamp (optional)
        limit: Max events to return (default: 100, max: 10000)

    Returns:
        List of EventLog objects, ordered by timestamp DESC

    Performance: <100ms for 10,000 events with indexes
    """
```

#### `export_events()`

```python
async def export_events(
    self,
    output_path: str | Path,
    format: str = "jsonl",
    filters: dict | None = None
) -> None:
    """
    Export event log to file.

    Args:
        output_path: Destination file path
        format: Export format ("jsonl", "csv", "json")
        filters: Same filters as query_events() (optional)

    Raises:
        ValueError: If format not supported
        OSError: If output_path not writable

    Performance: Streams results, memory efficient for large logs
    """
```

---

### Metrics and Monitoring

#### `get_metrics()`

```python
def get_metrics(self) -> dict:
    """
    Get runtime performance metrics.

    Returns:
        dict with keys:
            - uptime_seconds: float - Runtime uptime
            - total_agents: int - Total registered agents
            - running_agents: int - Currently running agents
            - total_tasks: int - Total submitted tasks
            - completed_tasks: int - Successfully completed tasks
            - failed_tasks: int - Failed tasks
            - avg_task_duration_seconds: float - Mean task execution time
            - p95_task_duration_seconds: float - 95th percentile duration
            - messages_sent: int - Total inter-agent messages
            - avg_message_latency_ms: float - Mean message delivery time

    Note: Requires [monitoring] extra for detailed metrics
    Performance: <20ms
    """
```

#### `export_prometheus_metrics()`

```python
def export_prometheus_metrics(self) -> str:
    """
    Export metrics in Prometheus format.

    Returns:
        str: Prometheus-compatible metrics text

    Raises:
        RuntimeError: If [monitoring] extra not installed

    Usage:
        Can be exposed via HTTP endpoint for Prometheus scraping
    """
```

---

## Error Handling

All methods follow these error handling conventions:

1. **Validation Errors** (`ValueError`):
   - Invalid IDs (agent_id, task_id not found)
   - Invalid parameters (negative timeout, invalid enum values)
   - State violations (can't pause stopped agent)

2. **Runtime Errors** (`RuntimeError`):
   - Runtime not started when operation requires it
   - Resource limits exceeded
   - System state inconsistencies

3. **Process Errors** (`ProcessError`):
   - Agent process fails to start
   - Agent process becomes zombie
   - IPC communication failures

4. **Queue Errors** (`QueueFullError`):
   - Task queue at max capacity
   - Message queue full

5. **Timeout Errors** (`TimeoutError`):
   - wait_for_task() timeout
   - Graceful shutdown timeout

**Error Recovery**:
- All errors leave runtime in consistent state
- Failed operations are rolled back (database transactions)
- Errors logged to event log with full context

---

## Usage Examples

### Basic Runtime Lifecycle

```python
from miminions.runtime import AgentRuntime
from miminions.agents import BaseAgent

# Initialize runtime
runtime = AgentRuntime(
    storage_path="./my_runtime.db",
    config={"auto_recover": True}
)

# Start runtime
await runtime.start()

# Register an agent
agent_id = await runtime.register_agent(
    name="worker-1",
    agent_class=MyAgentClass,
    config={"model": "gpt-4"}
)

# Start the agent
await runtime.start_agent(agent_id)

# Submit a task
task_id = await runtime.submit_task(
    name="process-document",
    input_data={"document": "..."},
    priority=10
)

# Wait for completion
task = await runtime.wait_for_task(task_id, timeout_seconds=300)
print(task.output_data)

# Clean shutdown
await runtime.stop(graceful=True)
```

### Concurrent Multi-Agent Execution

```python
# Start multiple agents
agent_ids = []
for i in range(10):
    agent_id = await runtime.register_agent(
        name=f"worker-{i}",
        agent_class=WorkerAgent
    )
    await runtime.start_agent(agent_id)
    agent_ids.append(agent_id)

# Submit batch of tasks
task_ids = []
for item in batch_items:
    task_id = await runtime.submit_task(
        name=f"process-{item.id}",
        input_data={"item": item},
        priority=50
    )
    task_ids.append(task_id)

# Wait for all tasks
results = await asyncio.gather(
    *[runtime.wait_for_task(tid) for tid in task_ids]
)
```

### Task Dependencies

```python
# Task A (no dependencies)
task_a_id = await runtime.submit_task(
    name="download-data",
    input_data={"url": "..."}
)

# Task B (depends on Task A)
task_b_id = await runtime.submit_task(
    name="process-data",
    input_data={},
    dependencies=[task_a_id]  # Won't start until Task A completes
)

# Task C (depends on Task B)
task_c_id = await runtime.submit_task(
    name="upload-results",
    input_data={},
    dependencies=[task_b_id]  # Chain: A → B → C
)
```

---

## Performance Guarantees

Based on success criteria from spec.md:

- **SC-001**: Runtime supports 10+ concurrent agents without degradation
- **SC-002**: Task queue processes 100 tasks in <60 seconds
- **SC-008**: Status queries return in <1 second
- **SC-009**: Task throughput within 5% of theoretical max

**Latency Targets**:
- `get_agent_status()`: <10ms (p95)
- `get_task_status()`: <10ms (p95)
- `submit_task()`: <20ms (p95)
- `query_events()`: <100ms for 10K events (p95)

---

## Thread Safety

- `AgentRuntime` is **NOT thread-safe** for concurrent access
- Use a single runtime instance per process
- For multi-threaded applications, use asyncio locks or run runtime in dedicated thread
- Agent processes are fully isolated (safe by design)

---

## Versioning

This API follows semantic versioning:
- **MAJOR**: Breaking changes to public methods or behavior
- **MINOR**: New methods or optional parameters (backwards compatible)
- **PATCH**: Bug fixes (no API changes)

Current Version: **1.0.0**

---

**API Contract Status**: ✅ COMPLETE
**Ready for Implementation**: ✅ YES
