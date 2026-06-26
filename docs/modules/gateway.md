# Gateway

The `miminions.core.gateway` package is an **advanced, optional server-runtime layer**: a set of building blocks for wiring chat channels (Telegram, Discord, a WebSocket, your own transport) to an [agent](agent.md) core. It gives you an in-process async message bus, a uniform channel abstraction, session-scoped conversation state, cron scheduling, and phased startup/shutdown orchestration.

!!! warning "This is a toolkit, not a turnkey server"
    The gateway ships **building blocks, not a running server**. `BaseChannel` and `GatewayOrchestrator` are **abstract** — you subclass them to integrate a real platform. **No concrete channels ship built-in**, and there are **no CLI commands** for the gateway. Reach for it only when you are assembling a long-running, multi-channel deployment; for scripted or single-shot agent use, the plain [`Minion`](agent.md) API is all you need.

```python
from miminions.core.gateway import (
    MessageBus, InboundMessage, OutboundMessage,
    BaseChannel, ChannelManager,
    Session, SessionManager,
    CronService, CronJob, CronSchedule,
    GatewayOrchestrator, Lifecycle, Phase,
)
```

!!! note "Import path"
    These symbols live under `miminions.core.gateway`. They are also re-exported from `miminions.core`, but the gateway path is the explicit one. The top-level `import miminions` exposes nothing.

## Components at a glance

<div class="grid cards" markdown>

- :material-bus: **MessageBus** — in-process async pub/sub over `asyncio` queues. Needs a running event loop.
- :material-message-text: **InboundMessage / OutboundMessage** — the DTOs that flow across the bus.
- :material-power-plug: **BaseChannel / ChannelManager** — abstract channel interface plus a manager that starts/stops channels and routes replies.
- :material-history: **Session / SessionManager** — JSONL-persisted conversation history keyed by `channel:chat_id`.
- :material-clock-outline: **CronService / CronJob / CronSchedule** — one-shot, recurring, or cron-expression scheduling.
- :material-rocket-launch: **GatewayOrchestrator / Lifecycle / Phase** — ordered startup (`BUS → SERVICES → CHANNELS`), reverse shutdown.

</div>

## The Message Bus

`MessageBus` is the spine of the runtime. It owns two `asyncio.Queue`s — `inbound` (channel → agent) and `outbound` (agent → channel) — plus an optional topic-based pub/sub layer. Because it is built on `asyncio` queues, **all of its primary operations are coroutines and must run inside an event loop**.

```python
import asyncio
from miminions.core.gateway import MessageBus, InboundMessage

async def main():
    bus = MessageBus()  # default queue maxsize is 1000

    # A subscriber reacts to every inbound message without coupling to channels
    async def log_inbound(msg: InboundMessage) -> None:
        print(f"[{msg.channel}] {msg.sender_id}: {msg.content}")

    bus.subscribe("inbound", log_inbound)

    # A channel would normally publish this; here we do it directly
    await bus.publish_inbound(
        InboundMessage(
            channel="websocket",
            sender_id="user-1",
            chat_id="room-7",
            content="hello",
        )
    )

    # The agent side consumes from the inbound queue
    msg = await bus.consume_inbound()
    print(msg.session_key)  # "websocket:room-7"

asyncio.run(main())
```

`publish_inbound` / `publish_outbound` also fire the `"inbound"` / `"outbound"` topics, so subscribers see traffic as it flows. Use `bus.subscribe(topic, handler)` / `bus.unsubscribe(...)` for named topics and `await bus.emit(topic, data)` to broadcast a custom event. Subscriber exceptions are logged and swallowed — one bad handler will not break the bus.

| Method | Description |
|--------|-------------|
| `async publish_inbound(msg)` | Enqueue a channel message for the agent; notifies `"inbound"`. |
| `async consume_inbound() -> InboundMessage` | Await the next inbound message. |
| `async publish_outbound(msg)` | Enqueue an agent reply for channels; notifies `"outbound"`. |
| `async consume_outbound() -> OutboundMessage` | Await the next outbound message. |
| `subscribe(topic, handler)` / `unsubscribe(topic, handler)` | Register/remove an async topic handler. |
| `async emit(topic, data=None)` | Notify all subscribers of a topic. |
| `inbound_size` / `outbound_size` | Pending-message counts (properties). |

### Message DTOs

`InboundMessage` and `OutboundMessage` are plain dataclasses.

```python
from miminions.core.gateway import InboundMessage, OutboundMessage

incoming = InboundMessage(
    channel="telegram",
    sender_id="42",
    chat_id="-100123",
    content="What's the weather?",
)
incoming.session_key            # "telegram:-100123"  (channel:chat_id)

reply = OutboundMessage(
    channel="telegram",
    chat_id="-100123",
    content="Sunny.",
)
```

`InboundMessage.session_key` defaults to `f"{channel}:{chat_id}"`, or whatever you pass as `session_key_override` (handy for thread-scoped sessions). Both DTOs also carry `media: list[str]` and `metadata: dict` for channel-specific data.

## Channels

A **channel** adapts a chat platform to the bus. `BaseChannel` is abstract: subclass it and implement `start`, `stop`, and `send`. Inbound messages are forwarded with the inherited `_handle_message(...)` helper, which enforces the allow-list before publishing.

!!! warning "Channels deny by default"
    `BaseChannel.is_allowed` returns `False` when `allow_from` is empty — **an unconfigured channel rejects everyone**. Set `allow_from` on your config to a list of sender ids, or `["*"]` to allow all. An empty list also logs a startup warning.

```python
from miminions.core.gateway import BaseChannel, MessageBus, OutboundMessage

class EchoChannel(BaseChannel):
    name = "echo"

    async def start(self) -> None:
        # A real channel connects to the platform and loops, calling
        # self._handle_message(sender_id, chat_id, content) per message.
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        # A real channel would push msg.content to the platform here.
        print(f"-> {msg.chat_id}: {msg.content}")

class Config:
    allow_from = ["*"]   # allow everyone (use explicit ids in production)

bus = MessageBus()
channel = EchoChannel(Config(), bus)
```

`ChannelManager` tracks channels by `name`, starts them concurrently, and runs a background dispatcher that pulls from the bus's outbound queue and routes each `OutboundMessage` to `channels[msg.channel].send(...)`.

```python
from miminions.core.gateway import ChannelManager

manager = ChannelManager(bus)
manager.register(channel)         # keyed by channel.name

await manager.start_all()         # starts channels + outbound dispatcher
# ... run ...
await manager.stop_all()          # cancels the dispatcher, stops every channel
```

| `ChannelManager` member | Description |
|-------------------------|-------------|
| `register(channel)` / `unregister(name)` | Add/remove a channel by its `name`. |
| `async start_all()` | Start every channel plus the outbound dispatcher. |
| `async stop_all()` | Stop the dispatcher and all channels. |
| `get_channel(name)` | Look up a channel, or `None`. |
| `get_status()` / `enabled_channels` | Per-channel running state / list of names. |

## Sessions

`SessionManager` persists per-conversation history as JSONL files in a directory you choose, with an in-memory cache and a TTL (default 3600s). A `Session` is keyed by the conversation (typically `InboundMessage.session_key`).

```python
from pathlib import Path
from miminions.core.gateway import SessionManager

sessions = SessionManager(Path.home() / ".miminions" / "gateway_sessions")

session = sessions.get_or_create("telegram:-100123")
session.add_message("user", "Hi", channel="telegram", sender_id="42")
session.add_message("assistant", "Hello!", channel="telegram")
sessions.save(session)                      # writes <key>.jsonl

history = session.get_history(max_messages=50)   # aligned to a user-turn boundary
all_sessions = sessions.list_sessions()          # newest-updated first
```

| `SessionManager` member | Description |
|-------------------------|-------------|
| `get_or_create(key) -> Session` | Cache-or-load-or-create a session. |
| `save(session)` | Persist to `<key>.jsonl` and refresh the cache. |
| `delete(key) -> bool` | Remove a session from disk and cache. |
| `invalidate(key)` | Drop a session from the in-memory cache only. |
| `list_sessions() -> list[dict]` | Metadata for all persisted sessions. |

`Session.add_message(role, content, channel="", sender_id=None, chat_id=None, **kwargs)` appends to an in-memory list; `get_history(max_messages=500)` returns the recent tail trimmed to start on a `user` turn; `clear()` empties it.

## Cron scheduling

`CronService` fires jobs on a schedule and invokes an `on_job` callback when they are due. Three schedule kinds are supported via `CronSchedule`:

=== "One-shot (`at`)"

    ```python
    import time
    from miminions.core.gateway import CronSchedule

    in_one_minute = int(time.time() * 1000) + 60_000
    schedule = CronSchedule(kind="at", at_ms=in_one_minute)
    ```

    Fires once at the given epoch-millisecond timestamp, then disables itself
    (or deletes itself if `delete_after_run=True`).

=== "Recurring (`every`)"

    ```python
    from miminions.core.gateway import CronSchedule

    # Every 15 minutes
    schedule = CronSchedule(kind="every", every_ms=15 * 60 * 1000)
    ```

=== "Cron expression (`cron`)"

    ```python
    from miminions.core.gateway import CronSchedule

    # 09:00 daily — requires the optional `croniter` package
    schedule = CronSchedule(kind="cron", expr="0 9 * * *", tz="UTC")
    ```

!!! warning "`cron` expressions need an optional dependency"
    The `kind="cron"` path imports **`croniter`**, which is **not installed by default**. Without it, the next-run computation logs a warning and returns `None`, so **the job never fires**. Install it with `pip install croniter` if you need cron expressions. The `at` and `every` kinds have no extra dependency. `tz` is only valid with `cron` schedules.

```python
import asyncio
from pathlib import Path
from miminions.core.gateway import CronService, CronJob, CronSchedule

async def on_job(job: CronJob) -> str | None:
    # Called when a job is due — e.g. trigger an agent turn
    print(f"firing {job.name}: {job.payload.message}")
    return None

async def main():
    cron = CronService(Path.home() / ".miminions" / "cron.json", on_job=on_job)
    await cron.start()                      # loads the store, arms the timer

    cron.add_job(
        name="daily-standup",
        schedule=CronSchedule(kind="every", every_ms=60_000),
        message="Summarize overnight activity",
    )
    # ... let it run ...
    await cron.stop()

asyncio.run(main())
```

!!! note "Cron mutation runs inside the loop"
    `start`, `stop`, and `run_job` are coroutines, and `add_job` / `remove_job` / `enable_job` re-arm the internal `asyncio` timer — call them from **within a running event loop** so the next tick is scheduled. Jobs are persisted as JSON at `store_path`.

| `CronService` member | Description |
|----------------------|-------------|
| `async start()` / `async stop()` | Load the store, arm/cancel the timer. |
| `add_job(name, schedule, message, deliver=False, channel=None, to=None, delete_after_run=False) -> CronJob` | Register a new job. |
| `remove_job(job_id) -> bool` | Delete a job by id. |
| `enable_job(job_id, enabled=True) -> CronJob \| None` | Enable/disable a job. |
| `list_jobs(include_disabled=False) -> list[CronJob]` | List jobs, sorted by next run. |
| `async run_job(job_id, force=False) -> bool` | Fire a job immediately. |
| `status() -> dict` | `running`, job count, and next wake time. |

## Orchestration

`GatewayOrchestrator` wires the bus, services, and channels together and starts them in a fixed order — **`BUS → SERVICES → CHANNELS`** — shutting them down in reverse. It is abstract: subclass it, implement `configure()`, and `register(phase, component)` any object that satisfies the `Lifecycle` interface (`async start()` / `async stop()`). If any component fails to start, the orchestrator shuts down everything already started and re-raises.

```python
from miminions.core.gateway import GatewayOrchestrator, Lifecycle, Phase

class CronLifecycle(Lifecycle):
    def __init__(self, cron):
        self.cron = cron
    async def start(self): await self.cron.start()
    async def stop(self): await self.cron.stop()

class ChannelLifecycle(Lifecycle):
    def __init__(self, manager):
        self.manager = manager
    async def start(self): await self.manager.start_all()
    async def stop(self): await self.manager.stop_all()

class MyGateway(GatewayOrchestrator):
    def __init__(self, cron, channels):
        super().__init__()
        self.cron = cron
        self.channels = channels

    async def configure(self) -> None:
        self.register(Phase.SERVICES, CronLifecycle(self.cron))
        self.register(Phase.CHANNELS, ChannelLifecycle(self.channels))

# gateway = MyGateway(cron, manager)
# await gateway.start()      # configure() + start each phase in order
# await gateway.shutdown()   # stop each phase in reverse
```

`Phase` is an `IntEnum` (`BUS=1`, `SERVICES=2`, `CHANNELS=3`) so phases sort naturally. `gateway.get_status()` returns the registered component class names per phase; `gateway.is_running` reflects lifecycle state.

## Putting it together

A typical deployment subclasses `GatewayOrchestrator`, and inside an agent-side consumer loop:

1. `await bus.consume_inbound()` to receive an `InboundMessage`;
2. load the matching `Session` from `SessionManager` for history;
3. call [`await minion.run(msg.content, message_history=...)`](agent.md);
4. append the turn to the session, then `await bus.publish_outbound(OutboundMessage(...))` so the `ChannelManager` dispatcher routes the reply back to the originating channel.

The framework supplies every piece above except the concrete channel transports and that consumer loop — those are yours to write.

## See Also

<div class="grid cards" markdown>

- :material-robot: **[Agent](agent.md)** — the `Minion` core the gateway drives
- :material-database: **[Memory](memory.md)** — vector and markdown memory backends
- :material-file-tree: **[Context Builder](context.md)** — what gets injected into the system prompt
- :material-wrench: **[Tools](tools.md)** — `@tool`, `create_tool`, and `GenericTool`

</div>
