# Messaging API Contract

**Feature**: 004-multi-agent-runtime
**Version**: 1.0.0
**Date**: 2025-10-19

## Overview

This document defines the inter-agent communication API for message passing between agents in the multi-agent runtime system. The messaging system supports direct messages, broadcasts, and request-response patterns with <100ms latency.

---

## Architecture

```
┌─────────────┐          ┌─────────────┐
│   Agent A   │          │   Agent B   │
│   Process   │          │   Process   │
└──────┬──────┘          └──────┬──────┘
       │                        │
       │ send_message()         │
       ▼                        ▼
┌──────────────────────────────────────┐
│        MessageBus (Shared Memory)     │
│   multiprocessing.Manager.Queue       │
└───────────────────┬──────────────────┘
                    │
                    │ poll_messages()
                    ▼
             ┌─────────────┐
             │   Agent C   │
             │   Process   │
             └─────────────┘
```

**Key Properties**:
- **Shared memory**: IPC via `multiprocessing.Manager`
- **Pub/sub pattern**: Agents subscribe to topics or direct channels
- **Non-blocking**: Message send/receive don't block agent task execution
- **Ordered**: Messages from Agent A to Agent B arrive in send order (FIFO)
- **Best-effort delivery**: Messages may be lost if recipient agent crashes

---

## Class: `MessageBus`

Central message routing system (managed by runtime).

### Constructor

```python
class MessageBus:
    def __init__(
        self,
        max_queue_size: int = 1000,
        message_ttl_seconds: int = 60
    ) -> None:
        """
        Initialize message bus.

        Args:
            max_queue_size: Maximum messages per agent mailbox
            message_ttl_seconds: Message expiry time (prevents memory leaks)

        Note: Typically created and managed by AgentRuntime, not user code.
        """
```

### Public Methods

#### `send_message()`

```python
async def send_message(
    self,
    sender_id: str,
    recipient_ids: list[str],
    message_type: str,
    data: dict,
    correlation_id: str | None = None,
    expires_at: datetime | None = None
) -> str:
    """
    Send message to one or more agents.

    Args:
        sender_id: Sending agent's ID (auto-filled by AgentContext)
        recipient_ids: List of recipient agent IDs (empty list = broadcast)
        message_type: Message category (e.g., "query", "response", "notification")
        data: Message payload (must be JSON-serializable, max 10MB)
        correlation_id: Optional ID linking request to response
        expires_at: Optional expiry time (default: now + message_ttl_seconds)

    Returns:
        message_id: UUID of created message

    Raises:
        ValueError: If recipient_ids contains invalid agent IDs
        QueueFullError: If recipient mailbox full
        MessageTooLargeError: If data exceeds 10MB after serialization

    Performance:
        - Direct message (1 recipient): ~0.1ms
        - Multicast (N recipients): ~0.1ms * N
        - Broadcast (all agents): ~0.1ms * active_agent_count

    Post-condition:
        - Message enqueued in recipient mailbox(es)
        - MESSAGE_SENT event logged
        - Recipient agents notified via polling
    """
```

#### `broadcast_message()`

```python
async def broadcast_message(
    self,
    sender_id: str,
    message_type: str,
    data: dict,
    correlation_id: str | None = None
) -> str:
    """
    Broadcast message to all running agents.

    Convenience wrapper for send_message(recipient_ids=[]).

    Args:
        sender_id: Sending agent's ID
        message_type: Message category
        data: Message payload (JSON-serializable)
        correlation_id: Optional correlation ID

    Returns:
        message_id: UUID of broadcast message

    Behavior:
        - Delivered to all agents with status = RUNNING or PAUSED
        - Not delivered to STOPPED or FAILED agents
        - Sender also receives copy (can filter by sender_id if needed)
    """
```

#### `receive_messages()`

```python
async def receive_messages(
    self,
    agent_id: str,
    block: bool = False,
    timeout_seconds: float | None = None
) -> list[AgentMessage]:
    """
    Receive pending messages for an agent.

    Args:
        agent_id: Receiving agent's ID
        block: If True, wait for messages to arrive
        timeout_seconds: Max wait time if block=True (None = wait forever)

    Returns:
        List of AgentMessage objects (may be empty if no messages)

    Raises:
        TimeoutError: If block=True and timeout reached with no messages

    Behavior:
        - Returns all pending messages (FIFO order)
        - Expired messages (timestamp > expires_at) are filtered out
        - Messages are removed from mailbox after retrieval (consume once)

    Performance:
        - Non-blocking: ~0.05ms (mailbox check)
        - Blocking: Depends on message arrival (polls every 10ms)
    """
```

#### `wait_for_response()`

```python
async def wait_for_response(
    self,
    agent_id: str,
    correlation_id: str,
    timeout_seconds: float = 30.0
) -> AgentMessage:
    """
    Wait for a specific response message (request-response pattern).

    Args:
        agent_id: Receiving agent's ID
        correlation_id: Correlation ID to match (from original request)
        timeout_seconds: Max wait time (default: 30s)

    Returns:
        AgentMessage: The matching response message

    Raises:
        TimeoutError: If no matching message received within timeout
        ValueError: If correlation_id is None

    Behavior:
        - Polls mailbox every 10ms for message with matching correlation_id
        - Other messages remain in mailbox for later retrieval
        - Returns immediately if matching message already in mailbox

    Usage:
        # Agent A sends query
        msg_id = await bus.send_message(
            sender_id="agent-a",
            recipient_ids=["agent-b"],
            message_type="query",
            data={"question": "..."},
            correlation_id="req-123"
        )

        # Agent A waits for response
        response = await bus.wait_for_response(
            agent_id="agent-a",
            correlation_id="req-123",
            timeout_seconds=30
        )
    """
```

---

## Data Model: `AgentMessage`

```python
@dataclass
class AgentMessage:
    """
    Inter-agent message.

    See data-model.md for full entity specification.
    """

    message_id: str
    """UUID of message"""

    sender_id: str
    """Sending agent ID"""

    recipient_ids: list[str]
    """Target agent IDs (empty = broadcast)"""

    message_type: str
    """Message category (e.g., 'query', 'response', 'notification')"""

    data: dict
    """Message payload (JSON-serializable)"""

    timestamp: datetime
    """Message creation time"""

    correlation_id: str | None = None
    """Links request to response (optional)"""

    expires_at: datetime | None = None
    """Message expiry time (optional)"""

    def is_expired(self) -> bool:
        """Check if message has expired."""
        return self.expires_at is not None and datetime.now() > self.expires_at

    def is_broadcast(self) -> bool:
        """Check if message is a broadcast."""
        return len(self.recipient_ids) == 0
```

---

## AgentContext Integration

Agents access messaging via `AgentContext`:

```python
class AgentContext:
    """
    Context injected into agents (see agent-interface.md).
    """

    async def send_message(
        self,
        recipient_ids: list[str],
        message_type: str,
        data: dict,
        correlation_id: str | None = None
    ) -> str:
        """
        Send message to other agents.

        Convenience wrapper that auto-fills sender_id.
        """
        return await self.message_bus.send_message(
            sender_id=self.agent_id,  # Auto-filled
            recipient_ids=recipient_ids,
            message_type=message_type,
            data=data,
            correlation_id=correlation_id
        )

    async def broadcast_message(
        self,
        message_type: str,
        data: dict
    ) -> str:
        """
        Broadcast message to all agents.

        Convenience wrapper that auto-fills sender_id.
        """
        return await self.message_bus.broadcast_message(
            sender_id=self.agent_id,  # Auto-filled
            message_type=message_type,
            data=data
        )

    async def receive_messages(
        self,
        block: bool = False,
        timeout_seconds: float | None = None
    ) -> list[AgentMessage]:
        """
        Receive pending messages for this agent.

        Convenience wrapper that auto-fills agent_id.
        """
        return await self.message_bus.receive_messages(
            agent_id=self.agent_id,  # Auto-filled
            block=block,
            timeout_seconds=timeout_seconds
        )

    async def wait_for_response(
        self,
        correlation_id: str,
        timeout_seconds: float = 30.0
    ) -> AgentMessage:
        """
        Wait for response message with matching correlation_id.

        Convenience wrapper that auto-fills agent_id.
        """
        return await self.message_bus.wait_for_response(
            agent_id=self.agent_id,  # Auto-filled
            correlation_id=correlation_id,
            timeout_seconds=timeout_seconds
        )
```

---

## Communication Patterns

### Pattern 1: Direct Message (Fire-and-Forget)

```python
class NotifierAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Send notification to another agent
        await self.context.send_message(
            recipient_ids=["other-agent-id"],
            message_type="notification",
            data={"event": "task_completed", "task_id": task.task_id}
        )
        return {"status": "notification_sent"}
```

### Pattern 2: Request-Response

```python
class QueryAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Generate correlation ID
        correlation_id = str(uuid.uuid4())

        # Send query
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
            return {"error": "No response received"}


class HelperAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Check for incoming queries
        messages = await self.context.receive_messages(block=False)

        for msg in messages:
            if msg.message_type == "query":
                # Process query
                answer = self._process_query(msg.data["question"])

                # Send response with same correlation_id
                await self.context.send_message(
                    recipient_ids=[msg.sender_id],
                    message_type="response",
                    data={"answer": answer},
                    correlation_id=msg.correlation_id  # Link response to request
                )

        return {"queries_processed": len(messages)}
```

### Pattern 3: Broadcast (Pub/Sub)

```python
class BroadcasterAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Broadcast event to all agents
        await self.context.broadcast_message(
            message_type="event",
            data={"event_name": "system_alert", "severity": "high"}
        )
        return {"status": "broadcast_sent"}


class SubscriberAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        # Listen for broadcasts
        messages = await self.context.receive_messages(block=True, timeout_seconds=5)

        events = [
            msg.data for msg in messages
            if msg.message_type == "event" and msg.is_broadcast()
        ]

        return {"events_received": len(events), "events": events}
```

### Pattern 4: Multi-Agent Coordination

```python
class CoordinatorAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        """Coordinate multiple worker agents."""
        worker_ids = ["worker-1", "worker-2", "worker-3"]
        correlation_id = str(uuid.uuid4())

        # Send work to all workers
        for worker_id in worker_ids:
            await self.context.send_message(
                recipient_ids=[worker_id],
                message_type="work_request",
                data={"task_data": task.input_data},
                correlation_id=correlation_id
            )

        # Collect responses
        results = []
        for _ in worker_ids:
            try:
                response = await self.context.wait_for_response(
                    correlation_id=correlation_id,
                    timeout_seconds=60
                )
                results.append(response.data["result"])
            except TimeoutError:
                self.context.logger.warning(f"Worker timeout")

        return {"results": results, "success_count": len(results)}


class WorkerAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        """Process work requests from coordinator."""
        messages = await self.context.receive_messages(block=False)

        for msg in messages:
            if msg.message_type == "work_request":
                # Process work
                result = self._do_work(msg.data["task_data"])

                # Send result back
                await self.context.send_message(
                    recipient_ids=[msg.sender_id],
                    message_type="response",
                    data={"result": result},
                    correlation_id=msg.correlation_id
                )

        return {"messages_processed": len(messages)}
```

### Pattern 5: Message Filtering

```python
class FilteringAgent(BaseAgent):
    async def execute_task(self, task: Task) -> dict:
        """Process only specific message types."""
        messages = await self.context.receive_messages(block=False)

        # Filter by type
        queries = [m for m in messages if m.message_type == "query"]
        notifications = [m for m in messages if m.message_type == "notification"]

        # Filter by sender
        from_coordinator = [m for m in messages if m.sender_id == "coordinator-id"]

        # Filter by data content
        high_priority = [
            m for m in messages
            if m.data.get("priority") == "high"
        ]

        return {
            "queries": len(queries),
            "notifications": len(notifications),
            "from_coordinator": len(from_coordinator),
            "high_priority": len(high_priority)
        }
```

---

## Message Types (Conventions)

While `message_type` is a free-form string, these conventions are recommended:

| Type | Direction | Description | Requires correlation_id |
|------|-----------|-------------|-------------------------|
| `query` | Request | Ask for information | Optional (recommended) |
| `response` | Reply | Reply to query/command | Yes (matches request) |
| `command` | Request | Request action | Optional |
| `notification` | One-way | Inform of event | No |
| `event` | Broadcast | System-wide event | No |
| `acknowledgement` | Reply | Confirm receipt | Yes |
| `heartbeat` | Broadcast | Agent liveness signal | No |
| `data` | Any | Generic data transfer | No |

**Custom Types**: Agents can define custom message types for domain-specific communication.

---

## Error Handling

### Message Delivery Failures

- **Recipient not found**: `ValueError` raised immediately
- **Recipient mailbox full**: `QueueFullError` raised, sender should retry or drop message
- **Recipient crashed**: Message lost (best-effort delivery)
- **Message expired**: Silently filtered out during receive

### Timeout Handling

```python
# Robust request-response with timeout
try:
    response = await self.context.wait_for_response(
        correlation_id=correlation_id,
        timeout_seconds=30
    )
    # Process response
except TimeoutError:
    # Handle timeout (retry, fallback, error)
    self.context.logger.warning("No response received")
    return {"error": "timeout"}
```

### Message Validation

Agents should validate message data:

```python
messages = await self.context.receive_messages()

for msg in messages:
    # Validate required fields
    if "question" not in msg.data:
        self.context.logger.error(f"Invalid message from {msg.sender_id}")
        continue

    # Validate data types
    if not isinstance(msg.data["question"], str):
        self.context.logger.error("Invalid question type")
        continue

    # Process valid message
    await self._handle_query(msg)
```

---

## Performance Characteristics

### Latency Targets

- **Direct message (1 recipient)**: <1ms (p95)
- **Multicast (5 recipients)**: <5ms (p95)
- **Broadcast (10 agents)**: <10ms (p95)
- **Request-response round-trip**: <100ms (p95) - Success Criteria SC-004

### Throughput

- **Messages per second per agent**: 1000+ (send)
- **Messages per second per agent**: 1000+ (receive)
- **Total system throughput**: 10,000+ messages/sec with 10 agents

### Resource Usage

- **Memory per message**: ~1KB (header) + data size
- **Mailbox memory**: max_queue_size * avg_message_size (e.g., 1000 * 5KB = 5MB)
- **Total system memory**: ~50MB for 10 agents with full mailboxes

### Scalability Limits

- **Max concurrent agents**: 1000+ (limited by system resources, not messaging)
- **Max message size**: 10MB (configurable, larger messages use chunking)
- **Max mailbox size**: 1000 messages (configurable, prevents memory bloat)
- **Max message rate**: 10,000 msg/sec (system-wide)

---

## Testing

### Unit Testing Messages

```python
@pytest.mark.asyncio
async def test_send_receive():
    """Test basic message send/receive."""
    bus = MessageBus()

    # Send message
    msg_id = await bus.send_message(
        sender_id="agent-a",
        recipient_ids=["agent-b"],
        message_type="test",
        data={"key": "value"}
    )

    # Receive message
    messages = await bus.receive_messages(agent_id="agent-b")
    assert len(messages) == 1
    assert messages[0].message_id == msg_id
    assert messages[0].sender_id == "agent-a"
    assert messages[0].data["key"] == "value"
```

### Integration Testing Request-Response

```python
@pytest.mark.asyncio
async def test_request_response():
    """Test request-response pattern."""
    runtime = AgentRuntime()
    await runtime.start()

    # Register agents
    query_agent_id = await runtime.register_agent("query-agent", QueryAgent)
    helper_agent_id = await runtime.register_agent("helper-agent", HelperAgent)

    await runtime.start_agent(query_agent_id)
    await runtime.start_agent(helper_agent_id)

    # Submit task that triggers request-response
    task_id = await runtime.submit_task(
        name="test-query",
        input_data={"query": "test"}
    )

    # Wait for completion
    task = await runtime.wait_for_task(task_id, timeout_seconds=10)
    assert task.status == TaskStatus.COMPLETED
    assert "answer" in task.output_data

    await runtime.stop()
```

---

## Security Considerations

### Message Validation

- **Data sanitization**: Agents should validate incoming message data
- **Type checking**: Verify data types match expectations
- **Size limits**: Enforce max message size (10MB default)

### Access Control

- **Agent authentication**: Only registered agents can send messages
- **Recipient validation**: Only valid agent IDs accepted
- **No external access**: Message bus is internal to runtime process

### Privacy

- **No encryption**: Messages in shared memory are not encrypted
- **Process isolation**: Messages not accessible outside runtime process
- **Logging**: Message events logged but data not logged by default

---

## Versioning

Messaging API follows semantic versioning:
- **MAJOR**: Breaking changes to message format or behavior
- **MINOR**: New message patterns or optional features
- **PATCH**: Bug fixes

Current Version: **1.0.0**

---

**Messaging API Status**: ✅ COMPLETE
**Ready for Implementation**: ✅ YES
