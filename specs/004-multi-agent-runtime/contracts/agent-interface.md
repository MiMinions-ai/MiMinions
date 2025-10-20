# Agent Interface Contract

**Feature**: 004-multi-agent-runtime
**Version**: 1.0.0
**Date**: 2025-10-19

## Overview

This document defines the interface contract that all agents must implement to be compatible with the multi-agent runtime system. Agents can either inherit from `BaseAgent` (recommended) or implement the `AgentProtocol` (for framework-agnostic integration).

---

## Agent Execution Model

Agents execute in separate processes with the following lifecycle:

```
1. Process spawned by AgentRuntime
2. Agent initialized with config
3. Runtime calls on_start() hook
4. Agent enters task execution loop:
   a. Wait for task assignment (blocks)
   b. Receive task via IPC
   c. Call execute_task(task)
   d. Return result via IPC
   e. Repeat until stopped
5. Runtime calls on_stop() hook
6. Process terminates
```

---

## Base Class: `BaseAgent`

Recommended approach for implementing agents.

### Constructor

```python
class BaseAgent:
    def __init__(self, config: dict | None = None) -> None:
        """
        Initialize agent with configuration.

        Args:
            config: Agent-specific configuration dict.
                   Common keys:
                   - agent_id: str - Unique agent instance ID (set by runtime)
                   - name: str - Agent name (set by runtime)
                   - Additional keys defined by agent implementation

        Note: Constructor should be lightweight (<1s).
              Heavy initialization should go in on_start() hook.
        """
        self.config = config or {}
        self.agent_id = config.get("agent_id") if config else None
        self.name = config.get("name") if config else "unnamed"
```

### Core Methods

#### `execute_task()` (REQUIRED)

```python
async def execute_task(self, task: Task) -> dict:
    """
    Execute a task and return results.

    This is the primary method agents must implement.
    Called by runtime when task assigned to this agent.

    Args:
        task: Task object with:
            - task_id: str - Unique task ID
            - name: str - Task name
            - input_data: dict - Task input parameters
            - priority: int - Task priority
            - timeout_seconds: int | None - Max execution time

    Returns:
        dict: Task output (must be JSON-serializable)
            - Can contain any keys
            - Will be stored in task.output_data

    Raises:
        Any exception: Caught by runtime, task marked as FAILED
                      Exception message stored in task.error_message

    Performance Requirements:
        - Must respect task.timeout_seconds (if set)
        - Should check self.is_stopping() periodically for graceful shutdown
        - Should yield control (await) in long-running loops

    Example:
        async def execute_task(self, task: Task) -> dict:
            input_text = task.input_data["text"]
            result = await self.process_text(input_text)
            return {"result": result, "status": "success"}
    """
    raise NotImplementedError("Subclasses must implement execute_task()")
```

### Lifecycle Hooks (OPTIONAL)

Override these methods to customize agent behavior:

#### `on_start()`

```python
async def on_start(self) -> None:
    """
    Called once when agent process starts, before first task.

    Use for:
    - Loading models or resources
    - Establishing connections
    - Initializing state

    Raises:
        Any exception: Agent transitions to FAILED state

    Example:
        async def on_start(self) -> None:
            self.model = await load_model(self.config["model_name"])
            self.db = await connect_to_db()
    """
    pass  # Default: no-op
```

#### `on_stop()`

```python
async def on_stop(self) -> None:
    """
    Called once when agent process stops, after last task.

    Use for:
    - Releasing resources
    - Closing connections
    - Cleanup operations

    Note: Called even if agent failed or was force-stopped.
          Should be idempotent and safe to call multiple times.

    Example:
        async def on_stop(self) -> None:
            if hasattr(self, 'db'):
                await self.db.close()
            if hasattr(self, 'model'):
                self.model.unload()
    """
    pass  # Default: no-op
```

#### `on_pause()`

```python
async def on_pause(self) -> dict:
    """
    Called when runtime pauses agent.

    Returns:
        dict: Agent state to persist (must be JSON-serializable)
              This state will be passed to on_resume() later.

    Use for:
    - Saving in-progress work
    - Checkpointing state
    - Releasing temporary resources

    Example:
        async def on_pause(self) -> dict:
            return {
                "current_progress": self.progress,
                "partial_results": self.results
            }
    """
    return {}  # Default: no state saved
```

#### `on_resume()`

```python
async def on_resume(self, state: dict) -> None:
    """
    Called when runtime resumes agent from paused state.

    Args:
        state: State dict returned by on_pause()

    Use for:
    - Restoring in-progress work
    - Resuming from checkpoint

    Example:
        async def on_resume(self, state: dict) -> None:
            self.progress = state.get("current_progress", 0)
            self.results = state.get("partial_results", [])
    """
    pass  # Default: no-op
```

#### `on_error()`

```python
async def on_error(self, error: Exception, task: Task | None) -> None:
    """
    Called when error occurs during task execution.

    Args:
        error: The exception that was raised
        task: The task that failed (None if error outside task execution)

    Use for:
    - Logging additional context
    - Cleanup after error
    - Custom error handling

    Note: Error is still propagated to runtime after this hook.

    Example:
        async def on_error(self, error: Exception, task: Task | None) -> None:
            if task:
                self.log(f"Task {task.task_id} failed: {error}")
            await self.cleanup_resources()
    """
    pass  # Default: no-op
```

---

## Protocol: `AgentProtocol`

For framework-agnostic agents that don't want to inherit from `BaseAgent`.

```python
from typing import Protocol, runtime_checkable

@runtime_checkable
class AgentProtocol(Protocol):
    """
    Structural interface for agents.

    Any class implementing these methods can be used as an agent,
    regardless of inheritance hierarchy.
    """

    async def execute_task(self, task: Task) -> dict:
        """Execute a task (see BaseAgent.execute_task() for details)."""
        ...

    async def on_start(self) -> None:
        """Optional: Called on agent start."""
        ...

    async def on_stop(self) -> None:
        """Optional: Called on agent stop."""
        ...

    async def on_pause(self) -> dict:
        """Optional: Called on agent pause."""
        ...

    async def on_resume(self, state: dict) -> None:
        """Optional: Called on agent resume."""
        ...

    async def on_error(self, error: Exception, task: Task | None) -> None:
        """Optional: Called on error."""
        ...
```

**Usage**:
```python
class MyCustomAgent:
    # No inheritance required!

    async def execute_task(self, task: Task) -> dict:
        # Implementation
        return {"result": "..."}

# Runtime accepts any object matching AgentProtocol
assert isinstance(MyCustomAgent(), AgentProtocol)  # True
```

---

## Agent Utilities

### `AgentContext`

Injected by runtime, provides access to runtime services:

```python
@dataclass
class AgentContext:
    """
    Context object available to agents during execution.

    Injected as self.context by BaseAgent or passed to protocol agents.
    """

    agent_id: str
    """Unique agent instance ID"""

    runtime_id: str
    """Runtime instance ID"""

    message_bus: MessageBus
    """Inter-agent communication interface"""

    logger: logging.Logger
    """Agent-specific logger"""

    metrics: MetricsCollector | None
    """Metrics collector (None if [monitoring] extra not installed)"""

    def is_stopping(self) -> bool:
        """Check if agent should stop gracefully."""

    async def checkpoint(self, state: dict) -> None:
        """Manually save agent state."""

    async def send_message(
        self,
        recipient_ids: list[str],
        message_type: str,
        data: dict
    ) -> None:
        """Send message to other agents (see messaging-api.md)."""

    async def broadcast_message(
        self,
        message_type: str,
        data: dict
    ) -> None:
        """Broadcast message to all agents."""
```

**Access in BaseAgent**:
```python
class MyAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Check if stopping
        if self.context.is_stopping():
            return {"status": "cancelled"}

        # Send message to another agent
        await self.context.send_message(
            recipient_ids=["other-agent-id"],
            message_type="query",
            data={"question": "..."}
        )

        # Log progress
        self.context.logger.info("Processing task...")

        return {"result": "..."}
```

---

## Example Implementations

### Example 1: Simple Synchronous Agent

```python
class SimpleAgent(BaseAgent):
    """Agent that processes text synchronously."""

    async def execute_task(self, task: Task) -> dict:
        # Extract input
        text = task.input_data.get("text", "")

        # Process (synchronous operation wrapped in async)
        result = self._process_text(text)

        # Return output
        return {"processed": result}

    def _process_text(self, text: str) -> str:
        """Synchronous helper method."""
        return text.upper()
```

### Example 2: Agent with External API

```python
import httpx

class APIAgent(BaseAgent):
    """Agent that calls external API."""

    async def on_start(self) -> None:
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient()

    async def on_stop(self) -> None:
        """Close HTTP client."""
        await self.client.aclose()

    async def execute_task(self, task: Task) -> dict:
        """Call API with task input."""
        url = task.input_data["url"]
        response = await self.client.get(url)
        return {"status": response.status_code, "body": response.text}
```

### Example 3: Stateful Agent with Pause/Resume

```python
class StatefulAgent(BaseAgent):
    """Agent that maintains state across tasks."""

    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.processed_count = 0
        self.results = []

    async def execute_task(self, task: Task) -> dict:
        """Process task and update state."""
        result = self._process(task.input_data)
        self.processed_count += 1
        self.results.append(result)
        return {"result": result, "total_processed": self.processed_count}

    async def on_pause(self) -> dict:
        """Save state on pause."""
        return {
            "processed_count": self.processed_count,
            "results": self.results
        }

    async def on_resume(self, state: dict) -> None:
        """Restore state on resume."""
        self.processed_count = state.get("processed_count", 0)
        self.results = state.get("results", [])

    def _process(self, data: dict) -> str:
        return f"Processed: {data}"
```

### Example 4: Agent with Inter-Agent Communication

```python
class CollaborativeAgent(BaseAgent):
    """Agent that communicates with other agents."""

    async def execute_task(self, task: Task) -> dict:
        """Execute task with help from other agents."""
        # Ask another agent for help
        await self.context.send_message(
            recipient_ids=["helper-agent-id"],
            message_type="query",
            data={"question": "Can you process this?", "data": task.input_data}
        )

        # Wait for response (see messaging-api.md for details)
        response = await self._wait_for_response(timeout=30)

        # Use response in our processing
        result = self._combine_results(task.input_data, response)

        return {"result": result}

    async def _wait_for_response(self, timeout: float) -> dict:
        """Wait for response message (implementation in messaging-api.md)."""
        # Simplified - actual implementation would use message bus
        pass
```

### Example 5: Framework-Agnostic Agent (No Inheritance)

```python
class FrameworkAgnosticAgent:
    """Agent using protocol, no inheritance."""

    def __init__(self, config: dict | None = None):
        self.config = config or {}

    async def execute_task(self, task: Task) -> dict:
        """Required by AgentProtocol."""
        return {"result": "processed"}

    async def on_start(self) -> None:
        """Optional lifecycle hook."""
        print(f"Agent {self.config.get('name')} started")

    async def on_stop(self) -> None:
        """Optional lifecycle hook."""
        print("Agent stopped")

# No BaseAgent inheritance required!
# Runtime accepts this via structural typing
```

---

## Error Handling

### Task Execution Errors

If `execute_task()` raises an exception:
1. Runtime catches exception
2. Task status → FAILED
3. Exception message stored in `task.error_message`
4. `on_error()` hook called (if implemented)
5. Agent remains RUNNING (ready for next task)

### Lifecycle Hook Errors

If any hook raises an exception:
- `on_start()`: Agent status → FAILED, process terminated
- `on_stop()`: Error logged, process terminated anyway
- `on_pause()`: Pause operation fails, agent remains RUNNING
- `on_resume()`: Resume operation fails, agent status → FAILED
- `on_error()`: Error logged, original error still propagated

### Graceful Shutdown

Agents should check `self.context.is_stopping()` in long-running tasks:

```python
async def execute_task(self, task: Task) -> dict:
    results = []
    for item in large_batch:
        # Check if stopping
        if self.context.is_stopping():
            # Save partial results
            await self.context.checkpoint({"partial": results})
            return {"status": "interrupted", "results": results}

        # Process item
        result = await self.process(item)
        results.append(result)

    return {"status": "completed", "results": results}
```

---

## Performance Guidelines

### Do's
- ✅ Use `async`/`await` for I/O operations
- ✅ Check `is_stopping()` in long-running loops
- ✅ Return JSON-serializable results
- ✅ Handle expected errors gracefully
- ✅ Release resources in `on_stop()`

### Don'ts
- ❌ Block the event loop with CPU-intensive sync code
- ❌ Ignore `task.timeout_seconds`
- ❌ Store large objects in memory indefinitely
- ❌ Use global state (agents run in separate processes)
- ❌ Assume task order or agent assignment

### CPU-Intensive Work

For CPU-bound operations, use thread pool executor:

```python
import concurrent.futures

class CPUIntensiveAgent(BaseAgent):
    async def on_start(self) -> None:
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=4)

    async def execute_task(self, task: Task) -> dict:
        # Offload CPU work to thread pool
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            self.executor,
            self._cpu_intensive_work,
            task.input_data
        )
        return {"result": result}

    def _cpu_intensive_work(self, data: dict) -> str:
        # Synchronous CPU-bound function
        return "processed"

    async def on_stop(self) -> None:
        self.executor.shutdown(wait=True)
```

---

## Testing Agents

### Unit Testing

```python
import pytest
from miminions.runtime import Task

@pytest.mark.asyncio
async def test_agent_execution():
    """Test agent executes task correctly."""
    agent = MyAgent(config={"setting": "value"})
    await agent.on_start()

    task = Task(
        task_id="test-task-id",
        name="test-task",
        input_data={"input": "data"},
        priority=50,
        status=TaskStatus.PENDING,
        created_at=datetime.now()
    )

    result = await agent.execute_task(task)

    assert result["status"] == "success"
    assert "result" in result

    await agent.on_stop()
```

### Integration Testing

```python
@pytest.mark.asyncio
async def test_agent_in_runtime():
    """Test agent executes in runtime."""
    runtime = AgentRuntime(storage_path=":memory:")
    await runtime.start()

    agent_id = await runtime.register_agent(
        name="test-agent",
        agent_class=MyAgent
    )
    await runtime.start_agent(agent_id)

    task_id = await runtime.submit_task(
        name="test-task",
        input_data={"input": "data"}
    )

    task = await runtime.wait_for_task(task_id, timeout_seconds=10)
    assert task.status == TaskStatus.COMPLETED
    assert task.output_data["status"] == "success"

    await runtime.stop()
```

---

## Versioning

Agent interface follows semantic versioning:
- **MAJOR**: Breaking changes to required methods or behavior
- **MINOR**: New optional hooks or utilities (backwards compatible)
- **PATCH**: Bug fixes (no interface changes)

Current Version: **1.0.0**

---

**Agent Interface Status**: ✅ COMPLETE
**Ready for Implementation**: ✅ YES
