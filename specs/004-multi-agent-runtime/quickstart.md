# Quick Start: Multi-Agent Runtime System

**Feature**: 004-multi-agent-runtime
**Date**: 2025-10-19

## Introduction

This guide walks through common usage patterns for the multi-agent runtime system, from basic single-agent execution to advanced multi-agent coordination patterns.

---

## Installation

```bash
# Core installation (minimal dependencies)
pip install miminions

# With monitoring support
pip install miminions[monitoring]

# Development installation
pip install miminions[dev]
```

---

## Example 1: Basic Agent Execution

Create and execute a simple agent:

```python
import asyncio
from miminions.runtime import AgentRuntime, BaseAgent, Task

# Define an agent
class HelloAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        name = task.input_data.get("name", "World")
        return {"greeting": f"Hello, {name}!"}

async def main():
    # Initialize runtime
    runtime = AgentRuntime(storage_path="./runtime.db")
    await runtime.start()

    # Register and start agent
    agent_id = await runtime.register_agent(
        name="hello-agent",
        agent_class=HelloAgent
    )
    await runtime.start_agent(agent_id)

    # Submit task
    task_id = await runtime.submit_task(
        name="greet-user",
        input_data={"name": "Alice"}
    )

    # Wait for result
    task = await runtime.wait_for_task(task_id, timeout_seconds=10)
    print(task.output_data)  # {"greeting": "Hello, Alice!"}

    # Shutdown
    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
{'greeting': 'Hello, Alice!'}
```

---

## Example 2: Concurrent Multi-Agent Execution

Run multiple agents in parallel:

```python
import asyncio
from miminions.runtime import AgentRuntime, BaseAgent, Task

class WorkerAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Simulate work
        await asyncio.sleep(2)
        item_id = task.input_data["item_id"]
        return {"processed_id": item_id, "status": "done"}

async def main():
    runtime = AgentRuntime()
    await runtime.start()

    # Start 5 worker agents
    agent_ids = []
    for i in range(5):
        agent_id = await runtime.register_agent(
            name=f"worker-{i}",
            agent_class=WorkerAgent
        )
        await runtime.start_agent(agent_id)
        agent_ids.append(agent_id)

    # Submit 20 tasks
    task_ids = []
    for i in range(20):
        task_id = await runtime.submit_task(
            name=f"process-item-{i}",
            input_data={"item_id": i}
        )
        task_ids.append(task_id)

    # Wait for all tasks to complete
    print(f"Submitted {len(task_ids)} tasks to {len(agent_ids)} agents")

    results = []
    for task_id in task_ids:
        task = await runtime.wait_for_task(task_id, timeout_seconds=60)
        results.append(task.output_data)

    print(f"Processed {len(results)} tasks successfully")
    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
Submitted 20 tasks to 5 agents
Processed 20 tasks successfully
```

**Performance**: With 5 agents, 20 tasks complete in ~8 seconds (vs ~40 seconds single-threaded).

---

## Example 3: Task Priorities and Dependencies

Control task execution order:

```python
async def main():
    runtime = AgentRuntime()
    await runtime.start()

    # Start agent
    agent_id = await runtime.register_agent("worker", WorkerAgent)
    await runtime.start_agent(agent_id)

    # Task A: High priority, no dependencies
    task_a_id = await runtime.submit_task(
        name="download-data",
        input_data={"url": "..."},
        priority=0  # High priority (0 = highest)
    )

    # Task B: Depends on Task A
    task_b_id = await runtime.submit_task(
        name="process-data",
        input_data={},
        priority=50,  # Medium priority
        dependencies=[task_a_id]  # Wait for Task A
    )

    # Task C: Depends on Task B
    task_c_id = await runtime.submit_task(
        name="upload-results",
        input_data={},
        priority=50,
        dependencies=[task_b_id]  # Wait for Task B
    )

    # Task D: Low priority, independent
    task_d_id = await runtime.submit_task(
        name="cleanup",
        input_data={},
        priority=100  # Low priority (100 = lowest)
    )

    # Execution order: A → B → C, with D executed when agent available
    # (D may run before B/C if it gets scheduled early)

    await runtime.wait_for_task(task_c_id)  # Wait for entire chain
    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Execution Order**:
```
1. Task A (high priority, no deps) - starts immediately
2. Task D (low priority, no deps) - may start if agent available
3. Task B (medium priority, waits for A) - starts after A completes
4. Task C (medium priority, waits for B) - starts after B completes
```

---

## Example 4: Agent Lifecycle Management

Control agent start, pause, resume, stop:

```python
async def main():
    runtime = AgentRuntime()
    await runtime.start()

    # Register agent
    agent_id = await runtime.register_agent("worker", WorkerAgent)

    # Start agent
    await runtime.start_agent(agent_id)
    status = runtime.get_agent_status(agent_id)
    print(f"Agent status: {status.status}")  # "running"

    # Submit long-running task
    task_id = await runtime.submit_task(
        name="long-task",
        input_data={"duration": 60}
    )

    # Wait a bit, then pause agent
    await asyncio.sleep(5)
    await runtime.pause_agent(agent_id)
    print("Agent paused")

    # Resume after some time
    await asyncio.sleep(10)
    await runtime.resume_agent(agent_id)
    print("Agent resumed")

    # Wait for task completion
    await runtime.wait_for_task(task_id, timeout_seconds=120)

    # Stop agent gracefully
    await runtime.stop_agent(agent_id, graceful=True)
    print("Agent stopped")

    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
Agent status: running
Agent paused
Agent resumed
Agent stopped
```

---

## Example 5: Inter-Agent Communication

Agents communicate via messages:

```python
from miminions.runtime import BaseAgent, Task, AgentMessage

class QueryAgent(BaseAgent):
    """Agent that asks questions."""

    async def execute_task(self, task: Task) -> dict:
        import uuid
        correlation_id = str(uuid.uuid4())

        # Send query to helper agent
        await self.context.send_message(
            recipient_ids=["helper-agent-id"],
            message_type="query",
            data={"question": "What is 2+2?"},
            correlation_id=correlation_id
        )

        # Wait for response
        try:
            response = await self.context.wait_for_response(
                correlation_id=correlation_id,
                timeout_seconds=30
            )
            return {"answer": response.data["answer"]}
        except TimeoutError:
            return {"error": "No response"}


class HelperAgent(BaseAgent):
    """Agent that answers questions."""

    async def execute_task(self, task: Task) -> dict:
        # Check for queries
        messages = await self.context.receive_messages(block=False)

        for msg in messages:
            if msg.message_type == "query":
                # Process query
                question = msg.data["question"]
                answer = eval(question.replace("What is ", "").replace("?", ""))

                # Send response
                await self.context.send_message(
                    recipient_ids=[msg.sender_id],
                    message_type="response",
                    data={"answer": answer},
                    correlation_id=msg.correlation_id
                )

        return {"queries_processed": len(messages)}


async def main():
    runtime = AgentRuntime()
    await runtime.start()

    # Start both agents
    query_agent_id = await runtime.register_agent("query-agent", QueryAgent)
    helper_agent_id = await runtime.register_agent("helper-agent", HelperAgent)

    await runtime.start_agent(query_agent_id)
    await runtime.start_agent(helper_agent_id)

    # Submit tasks to both agents
    # (HelperAgent needs to be running to receive messages)
    helper_task_id = await runtime.submit_task(
        name="helper-listen",
        input_data={}
    )

    await asyncio.sleep(1)  # Let helper start listening

    query_task_id = await runtime.submit_task(
        name="query-task",
        input_data={}
    )

    # Wait for query to complete
    task = await runtime.wait_for_task(query_task_id, timeout_seconds=10)
    print(f"Query result: {task.output_data}")  # {"answer": 4}

    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
Query result: {'answer': 4}
```

---

## Example 6: Broadcast Messages

Agent broadcasts to all other agents:

```python
class BroadcasterAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Broadcast event
        await self.context.broadcast_message(
            message_type="alert",
            data={"message": "System maintenance in 5 minutes", "severity": "high"}
        )
        return {"status": "broadcast_sent"}


class ListenerAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Listen for broadcasts
        messages = await self.context.receive_messages(
            block=True,
            timeout_seconds=30
        )

        alerts = [
            msg.data for msg in messages
            if msg.message_type == "alert"
        ]

        return {"alerts_received": len(alerts), "alerts": alerts}


async def main():
    runtime = AgentRuntime()
    await runtime.start()

    # Start broadcaster + 3 listeners
    broadcaster_id = await runtime.register_agent("broadcaster", BroadcasterAgent)
    await runtime.start_agent(broadcaster_id)

    listener_ids = []
    for i in range(3):
        listener_id = await runtime.register_agent(f"listener-{i}", ListenerAgent)
        await runtime.start_agent(listener_id)
        listener_ids.append(listener_id)

    # Submit tasks
    # Listeners start first (need to be listening)
    listener_task_ids = []
    for i in range(3):
        task_id = await runtime.submit_task(
            name=f"listen-{i}",
            input_data={}
        )
        listener_task_ids.append(task_id)

    await asyncio.sleep(1)

    # Broadcaster sends
    await runtime.submit_task(name="broadcast", input_data={})

    # Check listener results
    for task_id in listener_task_ids:
        task = await runtime.wait_for_task(task_id, timeout_seconds=35)
        print(f"Listener received: {task.output_data['alerts_received']} alerts")

    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
Listener received: 1 alerts
Listener received: 1 alerts
Listener received: 1 alerts
```

---

## Example 7: Agent with External API

Agent that calls external services:

```python
import httpx

class APIAgent(BaseAgent):
    async def on_start(self) -> None:
        """Initialize HTTP client."""
        self.client = httpx.AsyncClient(timeout=30.0)
        self.context.logger.info("HTTP client initialized")

    async def on_stop(self) -> None:
        """Cleanup HTTP client."""
        await self.client.aclose()
        self.context.logger.info("HTTP client closed")

    async def execute_task(self, task: Task) -> dict:
        """Fetch data from API."""
        url = task.input_data["url"]

        try:
            response = await self.client.get(url)
            response.raise_for_status()

            return {
                "status": response.status_code,
                "data": response.json(),
                "success": True
            }
        except httpx.HTTPError as e:
            self.context.logger.error(f"API error: {e}")
            return {
                "error": str(e),
                "success": False
            }


async def main():
    runtime = AgentRuntime()
    await runtime.start()

    agent_id = await runtime.register_agent("api-agent", APIAgent)
    await runtime.start_agent(agent_id)

    # Fetch from API
    task_id = await runtime.submit_task(
        name="fetch-data",
        input_data={"url": "https://api.example.com/data"}
    )

    task = await runtime.wait_for_task(task_id, timeout_seconds=60)
    if task.output_data["success"]:
        print(f"API returned: {task.output_data['data']}")
    else:
        print(f"API error: {task.output_data['error']}")

    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 8: Stateful Agent with Pause/Resume

Agent maintains state across pause/resume:

```python
class StatefulAgent(BaseAgent):
    def __init__(self, config: dict | None = None):
        super().__init__(config)
        self.processed_count = 0
        self.total_items = 0

    async def execute_task(self, task: Task) -> dict:
        items = task.input_data.get("items", [])
        self.total_items += len(items)
        self.processed_count += len(items)

        return {
            "processed": len(items),
            "total_count": self.processed_count
        }

    async def on_pause(self) -> dict:
        """Save state when paused."""
        self.context.logger.info(f"Saving state: {self.processed_count} items")
        return {
            "processed_count": self.processed_count,
            "total_items": self.total_items
        }

    async def on_resume(self, state: dict) -> None:
        """Restore state when resumed."""
        self.processed_count = state.get("processed_count", 0)
        self.total_items = state.get("total_items", 0)
        self.context.logger.info(f"Restored state: {self.processed_count} items")


async def main():
    runtime = AgentRuntime()
    await runtime.start()

    agent_id = await runtime.register_agent("stateful-agent", StatefulAgent)
    await runtime.start_agent(agent_id)

    # Submit 3 tasks
    for i in range(3):
        task_id = await runtime.submit_task(
            name=f"process-batch-{i}",
            input_data={"items": list(range(10))}
        )
        await runtime.wait_for_task(task_id)

    # Pause agent
    await runtime.pause_agent(agent_id)
    print("Agent paused with state saved")

    # Resume agent
    await runtime.resume_agent(agent_id)
    print("Agent resumed with state restored")

    # Submit another task - should continue from saved count
    task_id = await runtime.submit_task(
        name="process-batch-3",
        input_data={"items": list(range(5))}
    )
    task = await runtime.wait_for_task(task_id)
    print(f"Total processed: {task.output_data['total_count']}")  # 35

    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
Agent paused with state saved
Agent resumed with state restored
Total processed: 35
```

---

## Example 9: Resource Limits

Configure resource limits:

```python
from miminions.runtime import AgentRuntime, ResourceLimit

async def main():
    # Custom resource limits
    limits = ResourceLimit(
        limit_id="custom-limits",
        name="custom",
        max_concurrent_agents=5,  # Max 5 agents at once
        max_memory_per_agent_mb=256,  # 256MB per agent
        max_task_queue_size=100,  # Max 100 pending tasks
        message_queue_max_size=500,
        task_timeout_seconds=300  # 5 minute default timeout
    )

    runtime = AgentRuntime(
        storage_path="./runtime.db",
        resource_limits=limits
    )
    await runtime.start()

    # Try to start 10 agents (only 5 will run, others queue)
    agent_ids = []
    for i in range(10):
        agent_id = await runtime.register_agent(f"worker-{i}", WorkerAgent)
        try:
            await runtime.start_agent(agent_id)
            print(f"Started agent {i}")
        except RuntimeError as e:
            print(f"Agent {i} queued: {e}")
        agent_ids.append(agent_id)

    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
Started agent 0
Started agent 1
Started agent 2
Started agent 3
Started agent 4
Agent 5 queued: Max concurrent agents reached
Agent 6 queued: Max concurrent agents reached
...
```

---

## Example 10: Event Log Queries

Query runtime events:

```python
from miminions.runtime import EventType, Severity

async def main():
    runtime = AgentRuntime(storage_path="./runtime.db")
    await runtime.start()

    # ... run some agents and tasks ...

    # Query all events
    all_events = runtime.query_events(limit=100)
    print(f"Total events: {len(all_events)}")

    # Query agent lifecycle events
    agent_events = runtime.query_events(
        event_type=EventType.AGENT_STARTED,
        limit=50
    )
    print(f"Agent start events: {len(agent_events)}")

    # Query errors
    errors = runtime.query_events(
        severity=Severity.ERROR,
        limit=50
    )
    print(f"Error events: {len(errors)}")

    # Query recent events
    from datetime import datetime, timedelta
    recent = runtime.query_events(
        since=datetime.now() - timedelta(hours=1),
        limit=100
    )
    print(f"Events in last hour: {len(recent)}")

    # Export events to file
    await runtime.export_events(
        output_path="./events.jsonl",
        format="jsonl"
    )
    print("Events exported to events.jsonl")

    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

---

## Example 11: Metrics and Monitoring

Track runtime metrics:

```python
async def main():
    runtime = AgentRuntime(
        config={"enable_metrics": True}  # Requires [monitoring] extra
    )
    await runtime.start()

    # ... run agents and tasks ...

    # Get runtime metrics
    metrics = runtime.get_metrics()
    print(f"Uptime: {metrics['uptime_seconds']:.2f}s")
    print(f"Running agents: {metrics['running_agents']}")
    print(f"Completed tasks: {metrics['completed_tasks']}")
    print(f"Avg task duration: {metrics['avg_task_duration_seconds']:.2f}s")
    print(f"P95 task duration: {metrics['p95_task_duration_seconds']:.2f}s")

    # Export Prometheus metrics
    try:
        prom_metrics = runtime.export_prometheus_metrics()
        print("Prometheus metrics available")
        # Serve via HTTP for Prometheus scraping
    except RuntimeError:
        print("Monitoring extra not installed")

    await runtime.stop()

if __name__ == "__main__":
    asyncio.run(main())
```

**Output**:
```
Uptime: 125.45s
Running agents: 5
Completed tasks: 142
Avg task duration: 2.34s
P95 task duration: 5.67s
Prometheus metrics available
```

---

## Common Patterns Summary

| Pattern | Use Case | Example |
|---------|----------|---------|
| **Single Agent** | Simple task execution | Example 1 |
| **Multi-Agent** | Parallel processing | Example 2 |
| **Dependencies** | Sequential workflows | Example 3 |
| **Lifecycle Control** | Start/pause/resume/stop | Example 4 |
| **Request-Response** | Agent coordination | Example 5 |
| **Broadcast** | System-wide notifications | Example 6 |
| **External API** | HTTP/database access | Example 7 |
| **Stateful** | Maintain agent state | Example 8 |
| **Resource Limits** | Control system resources | Example 9 |
| **Monitoring** | Track metrics and events | Examples 10, 11 |

---

## Best Practices

### 1. Error Handling

Always handle errors in `execute_task()`:

```python
async def execute_task(self, task: Task) -> dict:
    try:
        result = await self.risky_operation()
        return {"result": result, "success": True}
    except Exception as e:
        self.context.logger.error(f"Task failed: {e}")
        return {"error": str(e), "success": False}
```

### 2. Graceful Shutdown

Check `is_stopping()` in long-running tasks:

```python
async def execute_task(self, task: Task) -> dict:
    for item in large_batch:
        if self.context.is_stopping():
            return {"status": "interrupted", "progress": processed_count}

        await self.process(item)

    return {"status": "completed"}
```

### 3. Resource Cleanup

Always implement `on_stop()` for cleanup:

```python
async def on_start(self) -> None:
    self.db = await database.connect()

async def on_stop(self) -> None:
    if hasattr(self, 'db'):
        await self.db.close()
```

### 4. Timeout Handling

Set appropriate timeouts for operations:

```python
# Task-level timeout
task_id = await runtime.submit_task(
    name="long-task",
    input_data={},
    timeout_seconds=300  # 5 minutes
)

# Message response timeout
response = await self.context.wait_for_response(
    correlation_id=correlation_id,
    timeout_seconds=30
)
```

### 5. Logging

Use context logger for agent logs:

```python
async def execute_task(self, task: Task) -> dict:
    self.context.logger.info("Starting task")
    self.context.logger.debug(f"Input: {task.input_data}")
    # ... process ...
    self.context.logger.info("Task completed")
    return result
```

---

## Next Steps

1. **Read API Documentation**: See `contracts/` directory for detailed API specs
2. **Review Data Model**: See `data-model.md` for entity specifications
3. **Explore Research**: See `research.md` for architectural decisions
4. **Run Tests**: Check `tests/` directory for test examples
5. **Deploy**: Follow deployment guide for production setup

---

## Troubleshooting

### Issue: "RuntimeError: Runtime not started"

**Solution**: Call `await runtime.start()` before any operations.

### Issue: "QueueFullError: Task queue at capacity"

**Solution**: Increase `max_task_queue_size` in ResourceLimit or wait for tasks to complete.

### Issue: "TimeoutError: Task execution timeout"

**Solution**: Increase `timeout_seconds` when submitting task or in ResourceLimit defaults.

### Issue: Agent process becomes zombie

**Solution**: Runtime automatically cleans up zombie processes. Check event log for details.

### Issue: Messages not delivered

**Solution**: Verify recipient agent is RUNNING or PAUSED (not STOPPED).

---

## Support

- **Documentation**: See `contracts/` directory
- **Examples**: See `examples/` directory (when available)
- **Issues**: Report bugs on GitHub
- **Questions**: Open GitHub Discussion

---

**Quick Start Status**: ✅ COMPLETE
**Ready for Users**: ✅ YES
