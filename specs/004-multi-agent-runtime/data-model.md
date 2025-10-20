# Data Model: Multi-Agent Runtime System

**Feature**: 004-multi-agent-runtime
**Date**: 2025-10-19
**Status**: Design Phase

## Overview

This document defines the core entities, their relationships, validation rules, and state transitions for the multi-agent runtime system. The data model aligns with the SQLite persistence schema from research.md while providing a framework-agnostic representation suitable for Python pydantic models.

---

## Entity Diagram

```
┌─────────────────┐         ┌─────────────────┐
│  AgentRuntime   │◇────────│  AgentInstance  │
│                 │  1..*   │                 │
└─────────────────┘         └────────┬────────┘
         │                           │
         │ 1..*                      │ 0..1
         │                           │ assigned_to
         ▼                           │
┌─────────────────┐                 │
│   TaskQueue     │◇────────────────┘
│                 │         │
└────────┬────────┘         │
         │ 1..*             │ 1..*
         ▼                  ▼
┌─────────────────┐    ┌─────────────────┐
│      Task       │────│ TaskDependency  │
│                 │    │                 │
└─────────────────┘    └─────────────────┘
         │
         │ 1..*
         ▼
┌─────────────────┐
│   EventLog      │
│                 │
└─────────────────┘

┌─────────────────┐
│  AgentMessage   │ (separate communication graph)
│                 │
└─────────────────┘

┌─────────────────┐
│ ResourceLimit   │ (configuration entity)
│                 │
└─────────────────┘
```

**Legend**: ◇ = composition (lifetime dependency), ─ = association, 1..* = one-to-many

---

## Core Entities

### 1. AgentInstance

Represents a running agent within the runtime system.

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `agent_id` | `str` (UUID) | Yes | UUID v4 format | Unique identifier for the agent instance |
| `name` | `str` | Yes | 1-100 chars, alphanumeric + spaces | Human-readable agent name |
| `status` | `AgentStatus` (enum) | Yes | One of: running, paused, stopped, failed | Current lifecycle state |
| `process_id` | `int` | No | Positive integer | OS process ID (null if not started) |
| `task_id` | `str` (UUID) | No | Valid Task ID or null | Currently assigned task (null if idle) |
| `created_at` | `datetime` | Yes | ISO 8601 timestamp | Agent creation timestamp |
| `updated_at` | `datetime` | Yes | ISO 8601 timestamp | Last status update timestamp |
| `config` | `dict` | Yes | JSON-serializable dict | Agent-specific configuration |
| `error_message` | `str` | No | Max 1000 chars | Last error message (if status=failed) |
| `restart_count` | `int` | Yes | Non-negative | Number of times agent has been restarted |

**Enums**:
```python
class AgentStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"
```

**State Transitions**:
```
                    start()
        ┌─────────────────────┐
        │                     ▼
    [STOPPED] ──────────► [RUNNING]
        ▲                     │
        │                     │ pause()
        │                     ▼
        │                 [PAUSED]
        │                     │
        │  stop()             │ resume()
        └─────────────────────┘
                │
                │ on_error()
                ▼
            [FAILED]
                │
                │ restart()
                └──────► [STOPPED]
```

**Invariants**:
- `process_id` must be non-null when status = running or paused
- `process_id` must be null when status = stopped
- `task_id` must be null when status = stopped or failed
- `updated_at` must be >= `created_at`
- `error_message` should only be non-null when status = failed

**Relationships**:
- Belongs to: `AgentRuntime` (1:many)
- Executes: `Task` (0:1)
- Generates: `EventLog` entries (1:many)
- Limited by: `ResourceLimit` (many:1 configuration)

---

### 2. Task

Represents a unit of work to be executed by an agent.

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `task_id` | `str` (UUID) | Yes | UUID v4 format | Unique task identifier |
| `name` | `str` | Yes | 1-200 chars | Human-readable task name |
| `priority` | `int` | Yes | 0-100 (0=highest) | Execution priority |
| `status` | `TaskStatus` (enum) | Yes | One of: pending, running, completed, failed, cancelled | Task execution state |
| `assigned_agent_id` | `str` (UUID) | No | Valid AgentInstance ID or null | Agent currently executing this task |
| `input_data` | `dict` | Yes | JSON-serializable | Input parameters for task execution |
| `output_data` | `dict` | No | JSON-serializable | Task execution results (null until completed) |
| `created_at` | `datetime` | Yes | ISO 8601 timestamp | Task creation time |
| `started_at` | `datetime` | No | ISO 8601, > created_at | Execution start time |
| `completed_at` | `datetime` | No | ISO 8601, > started_at | Execution completion time |
| `timeout_seconds` | `int` | No | Positive integer | Max execution time (null = no timeout) |
| `retry_count` | `int` | Yes | Non-negative | Number of retry attempts (starts at 0) |
| `max_retries` | `int` | Yes | Non-negative | Maximum allowed retries (0 = no retries) |
| `error_message` | `str` | No | Max 2000 chars | Error details if status = failed |

**Enums**:
```python
class TaskStatus(str, Enum):
    PENDING = "pending"      # Waiting in queue
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"        # Execution failed
    CANCELLED = "cancelled"  # User-cancelled before completion
```

**Priority Levels** (convenience constants):
- `HIGH = 0`
- `MEDIUM = 50`
- `LOW = 100`

**State Transitions**:
```
[PENDING] ──assign_to_agent()──► [RUNNING]
    │                                │
    │ cancel()                       │ success()
    ▼                                ▼
[CANCELLED]                     [COMPLETED]

[RUNNING] ──on_error()──► [FAILED]
    │                        │
    │ timeout()              │ retry()
    └────────────────────────┴──────► [PENDING]
                                (if retry_count < max_retries)
```

**Invariants**:
- `started_at` must be >= `created_at` (if non-null)
- `completed_at` must be >= `started_at` (if non-null)
- `assigned_agent_id` must be non-null when status = running
- `output_data` should only be non-null when status = completed
- `error_message` should only be non-null when status = failed
- `retry_count` must be <= `max_retries`

**Relationships**:
- Belongs to: `TaskQueue` (many:1)
- Assigned to: `AgentInstance` (many:0..1)
- Depends on: `Task` (many:many via `TaskDependency`)
- Generates: `EventLog` entries (1:many)

---

### 3. TaskDependency

Represents a dependency relationship between tasks (directed edge in task DAG).

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `task_id` | `str` (UUID) | Yes | Valid Task ID | Dependent task (must wait) |
| `depends_on_task_id` | `str` (UUID) | Yes | Valid Task ID | Prerequisite task (must complete first) |

**Invariants**:
- `task_id` ≠ `depends_on_task_id` (task cannot depend on itself)
- No cycles allowed in dependency graph (enforced by topological sort on insertion)
- Both tasks must exist in the same `TaskQueue`

**Graph Properties**:
- Forms a Directed Acyclic Graph (DAG)
- Cycle detection required on insertion
- Topological sort determines execution order

**Validation Rules**:
```python
def validate_dependency(task_id: str, depends_on_task_id: str) -> bool:
    """Validate dependency doesn't create cycle."""
    # Build adjacency list from existing dependencies
    graph = build_dependency_graph()

    # Add proposed edge
    graph[task_id].add(depends_on_task_id)

    # Detect cycle using DFS
    if has_cycle(graph):
        raise ValueError(f"Dependency creates cycle: {task_id} -> {depends_on_task_id}")

    return True
```

**Relationships**:
- References: `Task` (many:1 for task_id)
- References: `Task` (many:1 for depends_on_task_id)

---

### 4. TaskQueue

Represents the priority queue managing pending and active tasks.

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `queue_id` | `str` (UUID) | Yes | UUID v4 format | Unique queue identifier |
| `name` | `str` | Yes | 1-100 chars | Queue name (e.g., "default", "high-priority") |
| `max_size` | `int` | Yes | Positive integer | Maximum pending tasks (prevents unbounded growth) |
| `created_at` | `datetime` | Yes | ISO 8601 timestamp | Queue creation time |
| `paused` | `bool` | Yes | Boolean | Whether queue is paused (no task assignment) |

**Computed Properties** (not persisted):
- `pending_count`: Number of tasks with status = pending
- `running_count`: Number of tasks with status = running
- `completed_count`: Number of tasks with status = completed
- `failed_count`: Number of tasks with status = failed

**Invariants**:
- `pending_count` must be <= `max_size`
- Cannot enqueue new task when `pending_count` = `max_size` (unless blocking)

**Operations**:
```python
class TaskQueue:
    def enqueue(self, task: Task) -> None:
        """Add task to queue. Raises QueueFullError if at capacity."""

    def dequeue(self) -> Task | None:
        """Get highest priority ready task (all dependencies met). Returns None if empty."""

    def get_ready_tasks(self) -> list[Task]:
        """Return all tasks ready for execution (dependencies satisfied)."""

    def mark_completed(self, task_id: str) -> None:
        """Mark task as completed, enqueue newly ready dependent tasks."""

    def pause(self) -> None:
        """Pause queue (no new assignments until resumed)."""

    def resume(self) -> None:
        """Resume queue assignments."""
```

**Relationships**:
- Belongs to: `AgentRuntime` (many:1)
- Contains: `Task` (1:many)

---

### 5. AgentMessage

Represents inter-agent communication message.

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `message_id` | `str` (UUID) | Yes | UUID v4 format | Unique message identifier |
| `sender_id` | `str` (UUID) | Yes | Valid AgentInstance ID | Sending agent |
| `recipient_ids` | `list[str]` | Yes | List of AgentInstance IDs (empty = broadcast) | Target agents |
| `message_type` | `str` | Yes | 1-50 chars, alphanumeric + underscore | Message category (e.g., "query", "response", "notification") |
| `data` | `dict` | Yes | JSON-serializable | Message payload |
| `timestamp` | `datetime` | Yes | ISO 8601 timestamp | Message creation time |
| `correlation_id` | `str` (UUID) | No | UUID v4 format | Links request to response (null for unsolicited messages) |
| `expires_at` | `datetime` | No | ISO 8601, > timestamp | Message expiry time (null = no expiry) |

**Message Types** (examples):
- `query`: Request for information
- `response`: Reply to a query (uses correlation_id)
- `notification`: One-way event notification
- `command`: Request for action
- `acknowledgement`: Confirmation of receipt

**Delivery Semantics**:
- **Direct message**: `recipient_ids` contains single agent ID
- **Broadcast**: `recipient_ids` is empty list → all agents receive
- **Multicast**: `recipient_ids` contains multiple agent IDs → only those receive

**Invariants**:
- `sender_id` must be a running or paused agent
- `recipient_ids` must contain valid agent IDs (for direct/multicast)
- `correlation_id` should be non-null for message_type = "response"
- `expires_at` must be > `timestamp` (if non-null)

**Relationships**:
- Sent by: `AgentInstance` (many:1)
- Received by: `AgentInstance` (many:many)

---

### 6. EventLog

Audit trail of all runtime events.

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `event_id` | `int` | Yes | Auto-incrementing | Sequential event ID |
| `timestamp` | `datetime` | Yes | ISO 8601 timestamp | Event occurrence time |
| `event_type` | `EventType` (enum) | Yes | Valid event type | Category of event |
| `agent_id` | `str` (UUID) | No | Valid AgentInstance ID or null | Related agent (null for system events) |
| `task_id` | `str` (UUID) | No | Valid Task ID or null | Related task (null for agent-only events) |
| `severity` | `Severity` (enum) | Yes | One of: debug, info, warning, error | Event severity level |
| `details` | `dict` | Yes | JSON-serializable | Event-specific data |

**Enums**:
```python
class EventType(str, Enum):
    # Agent lifecycle
    AGENT_STARTED = "agent_started"
    AGENT_PAUSED = "agent_paused"
    AGENT_RESUMED = "agent_resumed"
    AGENT_STOPPED = "agent_stopped"
    AGENT_FAILED = "agent_failed"
    AGENT_RESTARTED = "agent_restarted"

    # Task lifecycle
    TASK_ENQUEUED = "task_enqueued"
    TASK_ASSIGNED = "task_assigned"
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"
    TASK_TIMEOUT = "task_timeout"

    # Runtime events
    RUNTIME_STARTED = "runtime_started"
    RUNTIME_STOPPED = "runtime_stopped"
    QUEUE_PAUSED = "queue_paused"
    QUEUE_RESUMED = "queue_resumed"
    RESOURCE_LIMIT_EXCEEDED = "resource_limit_exceeded"

    # Communication events
    MESSAGE_SENT = "message_sent"
    MESSAGE_RECEIVED = "message_received"
    MESSAGE_EXPIRED = "message_expired"

class Severity(str, Enum):
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
```

**Details Field Examples**:
```python
# AGENT_FAILED event
details = {
    "error_message": "Division by zero in task execution",
    "traceback": "...",
    "process_exit_code": -11
}

# TASK_COMPLETED event
details = {
    "execution_time_seconds": 5.23,
    "output_size_bytes": 1024
}

# RESOURCE_LIMIT_EXCEEDED event
details = {
    "resource_type": "memory",
    "current_usage_mb": 520,
    "limit_mb": 512
}
```

**Invariants**:
- Events are immutable (append-only log)
- `event_id` is strictly increasing (sequential)
- At least one of `agent_id` or `task_id` should be non-null for most event types
- System events (runtime_*) have both `agent_id` and `task_id` as null

**Relationships**:
- References: `AgentInstance` (many:0..1)
- References: `Task` (many:0..1)

---

### 7. ResourceLimit

Configuration entity defining resource constraints.

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `limit_id` | `str` (UUID) | Yes | UUID v4 format | Unique limit configuration ID |
| `name` | `str` | Yes | 1-100 chars | Limit profile name (e.g., "default", "gpu-agent") |
| `max_concurrent_agents` | `int` | Yes | Positive integer | Maximum agents running simultaneously |
| `max_memory_per_agent_mb` | `int` | No | Positive integer | Memory limit per agent in MB (null = unlimited) |
| `max_cpu_time_per_agent_seconds` | `int` | No | Positive integer | CPU time limit per agent in seconds (null = unlimited) |
| `max_task_queue_size` | `int` | Yes | Positive integer | Maximum pending tasks in queue |
| `message_queue_max_size` | `int` | Yes | Positive integer | Max messages per agent mailbox |
| `task_timeout_seconds` | `int` | No | Positive integer | Default task timeout (null = no timeout) |

**Default Profile** (built-in):
```python
DEFAULT_LIMITS = ResourceLimit(
    limit_id="00000000-0000-0000-0000-000000000000",
    name="default",
    max_concurrent_agents=10,
    max_memory_per_agent_mb=512,
    max_cpu_time_per_agent_seconds=None,  # Unlimited
    max_task_queue_size=1000,
    message_queue_max_size=1000,
    task_timeout_seconds=3600  # 1 hour
)
```

**Enforcement Points**:
- `max_concurrent_agents`: Checked when starting new agent
- `max_memory_per_agent_mb`: Monitored every 5 seconds, agent paused/terminated if exceeded
- `max_cpu_time_per_agent_seconds`: OS-level limit via `resource.setrlimit()`
- `max_task_queue_size`: Checked when enqueuing task
- `message_queue_max_size`: Checked when sending message
- `task_timeout_seconds`: Timer started when task begins execution

**Relationships**:
- Applied to: `AgentRuntime` (1:1 configuration)

---

### 8. RuntimeState

Top-level runtime system state (singleton per runtime instance).

**Fields**:

| Field | Type | Required | Validation | Description |
|-------|------|----------|------------|-------------|
| `runtime_id` | `str` (UUID) | Yes | UUID v4 format | Unique runtime instance ID |
| `status` | `RuntimeStatus` (enum) | Yes | One of: starting, running, stopping, stopped | Runtime lifecycle state |
| `started_at` | `datetime` | Yes | ISO 8601 timestamp | Runtime initialization time |
| `stopped_at` | `datetime` | No | ISO 8601, > started_at | Runtime shutdown time |
| `resource_limit_id` | `str` (UUID) | Yes | Valid ResourceLimit ID | Active resource limit profile |
| `storage_path` | `str` | Yes | Valid file path | SQLite database path |
| `config` | `dict` | Yes | JSON-serializable | Runtime configuration options |

**Enums**:
```python
class RuntimeStatus(str, Enum):
    STARTING = "starting"  # Initialization in progress
    RUNNING = "running"    # Fully operational
    STOPPING = "stopping"  # Graceful shutdown in progress
    STOPPED = "stopped"    # Shut down
```

**State Transitions**:
```
[STOPPED] ──start()──► [STARTING] ──init_complete()──► [RUNNING]
                           │                              │
                           │                              │ stop()
                           │                              ▼
                           └──────────────────────────► [STOPPING]
                                                          │
                                                          │ cleanup_complete()
                                                          ▼
                                                       [STOPPED]
```

**Computed Properties**:
- `agent_count`: Number of agents in any state
- `running_agent_count`: Number of agents with status = running
- `task_count`: Total tasks across all queues
- `pending_task_count`: Tasks with status = pending
- `uptime_seconds`: Current time - started_at (if running)

**Relationships**:
- Contains: `AgentInstance` (1:many)
- Contains: `TaskQueue` (1:many)
- Uses: `ResourceLimit` (1:1 configuration)
- Generates: `EventLog` entries (1:many)

---

## Validation Rules

### Cross-Entity Constraints

1. **Agent-Task Assignment**:
   - An agent can only be assigned one task at a time
   - A task can only be assigned to one agent at a time
   - Running tasks must have an assigned agent

2. **Task Dependencies**:
   - Dependency graph must be acyclic (DAG)
   - All dependency references must point to existing tasks
   - A task cannot be assigned until all its dependencies are completed

3. **Resource Limits**:
   - `running_agent_count` must be <= `max_concurrent_agents`
   - `pending_task_count` must be <= `max_task_queue_size`
   - Agent memory usage must be <= `max_memory_per_agent_mb`

4. **Message Delivery**:
   - Sender agent must be running or paused
   - Recipient agents must exist (running, paused, or stopped)
   - Expired messages (timestamp > expires_at) should not be delivered

5. **Event Log Integrity**:
   - Events are immutable after creation
   - Events must reference valid agent/task IDs (or null)
   - Event IDs must be strictly increasing

---

## Persistence Mapping

Mapping between pydantic models and SQLite schema (from research.md):

| Entity | SQLite Table | Notes |
|--------|--------------|-------|
| `AgentInstance` | `agents` | `config` stored as JSON TEXT |
| `Task` | `tasks` | `input_data`, `output_data` stored as JSON TEXT |
| `TaskDependency` | `task_dependencies` | Composite primary key (task_id, depends_on_task_id) |
| `TaskQueue` | N/A | In-memory only (heapq), reconstructed from tasks on load |
| `AgentMessage` | N/A | In-memory only (IPC via multiprocessing.Manager) |
| `EventLog` | `events` | `details` stored as JSON TEXT, auto-increment ID |
| `ResourceLimit` | `resource_limits` (new) | Single row for active config |
| `RuntimeState` | `runtime_state` (new) | Singleton table, single row |

**New Tables Required**:
```sql
CREATE TABLE resource_limits (
    limit_id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    max_concurrent_agents INTEGER NOT NULL,
    max_memory_per_agent_mb INTEGER,
    max_cpu_time_per_agent_seconds INTEGER,
    max_task_queue_size INTEGER NOT NULL,
    message_queue_max_size INTEGER NOT NULL,
    task_timeout_seconds INTEGER
);

CREATE TABLE runtime_state (
    runtime_id TEXT PRIMARY KEY,
    status TEXT NOT NULL CHECK(status IN ('starting', 'running', 'stopping', 'stopped')),
    started_at REAL NOT NULL,
    stopped_at REAL,
    resource_limit_id TEXT NOT NULL,
    storage_path TEXT NOT NULL,
    config_json TEXT NOT NULL,
    FOREIGN KEY (resource_limit_id) REFERENCES resource_limits(limit_id)
);
```

---

## Example Scenarios

### Scenario 1: Agent Executes Task

```
1. Task created with status=pending, added to TaskQueue
2. Agent transitions to running, assigned task_id
3. Task status → running, assigned_agent_id set
4. EventLog: TASK_ASSIGNED, TASK_STARTED
5. Agent completes task → Task status=completed, output_data populated
6. Agent.task_id → null (idle)
7. EventLog: TASK_COMPLETED
8. TaskQueue checks for newly ready dependent tasks
```

### Scenario 2: Agent Crashes Mid-Task

```
1. Agent status=running, executing task
2. Process dies (simulated failure)
3. Runtime detects via process.is_alive() check
4. Agent status → failed, error_message set
5. Task status → failed (or pending if retry < max_retries)
6. EventLog: AGENT_FAILED, TASK_FAILED
7. Runtime decides: restart agent or leave stopped
8. No other agents affected (isolation verified)
```

### Scenario 3: Task with Dependencies

```
1. Task A submitted with depends_on=[Task B, Task C]
2. TaskDependency edges created: A→B, A→C
3. Task B completes → TaskQueue recalculates ready tasks
4. Task C still pending → Task A remains pending
5. Task C completes → Task A now ready (all deps satisfied)
6. Task A moved to heap, available for assignment
7. Next available agent assigned Task A
```

---

## Pydantic Model Skeletons

```python
from pydantic import BaseModel, Field, validator
from datetime import datetime
from enum import Enum
from typing import Optional

class AgentStatus(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    FAILED = "failed"

class AgentInstance(BaseModel):
    agent_id: str = Field(..., description="UUID v4")
    name: str = Field(..., min_length=1, max_length=100)
    status: AgentStatus
    process_id: Optional[int] = Field(None, gt=0)
    task_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    config: dict = Field(default_factory=dict)
    error_message: Optional[str] = Field(None, max_length=1000)
    restart_count: int = Field(0, ge=0)

    @validator('updated_at')
    def updated_after_created(cls, v, values):
        if 'created_at' in values and v < values['created_at']:
            raise ValueError('updated_at must be >= created_at')
        return v

    @validator('process_id')
    def process_id_constraints(cls, v, values):
        status = values.get('status')
        if status in (AgentStatus.RUNNING, AgentStatus.PAUSED) and v is None:
            raise ValueError(f'process_id required when status={status}')
        if status == AgentStatus.STOPPED and v is not None:
            raise ValueError('process_id must be null when status=stopped')
        return v

class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"

class Task(BaseModel):
    task_id: str = Field(..., description="UUID v4")
    name: str = Field(..., min_length=1, max_length=200)
    priority: int = Field(50, ge=0, le=100)
    status: TaskStatus
    assigned_agent_id: Optional[str] = None
    input_data: dict = Field(default_factory=dict)
    output_data: Optional[dict] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    timeout_seconds: Optional[int] = Field(None, gt=0)
    retry_count: int = Field(0, ge=0)
    max_retries: int = Field(0, ge=0)
    error_message: Optional[str] = Field(None, max_length=2000)

    @validator('started_at')
    def started_after_created(cls, v, values):
        if v and 'created_at' in values and v < values['created_at']:
            raise ValueError('started_at must be >= created_at')
        return v

    @validator('completed_at')
    def completed_after_started(cls, v, values):
        if v and 'started_at' in values and values['started_at'] and v < values['started_at']:
            raise ValueError('completed_at must be >= started_at')
        return v

    @validator('retry_count')
    def retry_within_max(cls, v, values):
        if 'max_retries' in values and v > values['max_retries']:
            raise ValueError('retry_count must be <= max_retries')
        return v

# Additional models follow similar patterns...
```

---

**Data Model Status**: ✅ COMPLETE
**Entities Defined**: 8 core entities with full specifications
**Validation Rules**: Comprehensive field and cross-entity constraints
**Ready for API Contract Design**: ✅ YES
