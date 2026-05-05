# Gateway — Persistent Server Runtime

The `gateway` module provides the core runtime infrastructure for running
MiMinions as a persistent, event-driven server. It is modelled after the
[nanobot](https://github.com/HKUDS/nanobot) architecture for channel
abstraction and message routing.

## Module Layout

```
core/gateway/
├── __init__.py        # Public API re-exports
├── events.py          # InboundMessage / OutboundMessage DTOs
├── bus.py             # In-process async message bus with pub/sub
├── channel.py         # BaseChannel ABC + ChannelManager
├── session.py         # Session-scoped conversation state (JSONL persistence)
├── services.py        # CronService (full cron expressions)
└── orchestrator.py    # Phased startup / graceful shutdown
```

## Components

### Message Bus (`bus.py`)

An in-process async message bus built on `asyncio.Queue`.

- **Inbound queue** — channels push `InboundMessage` objects to the agent.
- **Outbound queue** — the agent pushes `OutboundMessage` objects to channels.
- **Topic pub/sub** — `subscribe()` / `emit()` for event-driven workflows.

```python
from miminions.core.gateway import MessageBus

bus = MessageBus()
bus.subscribe("inbound", my_handler)
await bus.publish_inbound(msg)
await bus.emit("custom_event", payload)
```

### Channel Abstraction (`channel.py`)

Mirrors the nanobot `BaseChannel` interface. Each transport (Telegram,
Discord, WebSocket, HTTP SSE, etc.) subclasses `BaseChannel` and implements
`start()`, `stop()`, and `send()`.

`ChannelManager` coordinates channel lifecycle and routes outbound messages
to the correct channel by name.

```python
from miminions.core.gateway import BaseChannel, OutboundMessage

class MyChannel(BaseChannel):
    name = "my_channel"

    async def start(self) -> None:
        self._running = True
        # connect and listen ...

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        # deliver message ...
```

### Session State (`session.py`)

Session-scoped conversation history stored as a list of message dicts. Each
message carries its channel source, sender, and other DTO attributes.

- Configurable storage path via `SessionManager(storage_path=...)`.
- JSONL persistence (metadata header + one JSON object per message).

```python
from miminions.core.gateway import SessionManager

sessions = SessionManager(storage_path="/tmp/sessions")
session = sessions.get_or_create("telegram:12345")
session.add_message("user", "Hello!", channel="telegram", sender_id="12345")
sessions.save(session)
```

### Cron Service (`services.py`)

Persistent scheduled task execution with three schedule kinds:

| Kind    | Field      | Description                          |
|---------|------------|--------------------------------------|
| `at`    | `at_ms`    | One-shot at a specific timestamp     |
| `every` | `every_ms` | Recurring interval                   |
| `cron`  | `expr`     | Full cron expression (requires `croniter`) |

```python
from miminions.core.gateway import CronService, CronSchedule

cron = CronService(store_path=Path("cron/jobs.json"), on_job=my_handler)
await cron.start()

cron.add_job(
    name="daily-digest",
    schedule=CronSchedule(kind="cron", expr="0 9 * * *", tz="US/Eastern"),
    message="Generate daily digest",
)
```

### Startup Orchestrator (`orchestrator.py`)

Abstract base for phased startup and graceful shutdown:

| Phase      | Order | Examples                  |
|------------|-------|---------------------------|
| `BUS`      | 1     | MessageBus                |
| `SERVICES` | 2     | CronService               |
| `CHANNELS` | 3     | ChannelManager, listeners |

Shutdown runs in **reverse order** (CHANNELS → SERVICES → BUS).

```python
from miminions.core.gateway import GatewayOrchestrator, Phase, Lifecycle

class MyGateway(GatewayOrchestrator):
    async def configure(self) -> None:
        self.register(Phase.BUS,      bus_lifecycle)
        self.register(Phase.SERVICES,  cron_lifecycle)
        self.register(Phase.CHANNELS,  channel_lifecycle)

gateway = MyGateway()
await gateway.start()
# ... running ...
await gateway.shutdown()
```

## Dependencies

| Package    | Required | Notes                                   |
|------------|----------|-----------------------------------------|
| `croniter` | Optional | Required for `cron`-kind schedules only |

## Gateway CLI

The gateway runtime is exposed through a focused CLI that avoids raw bus,
event, and channel internals:

```bash
miminions gateway status --workspace my-ws
miminions gateway cron list --workspace my-ws
miminions gateway sessions list --workspace my-ws
```

Gateway storage is rooted in the workspace folder:

- `sessions/gateway/` for gateway session JSONL files
- `data/gateway/cron/jobs.json` for scheduled jobs

## Roadmap / Next Steps

- **Distributed message bus backends** — Add adapter hooks so the
  `MessageBus` can be backed by Redis Pub/Sub, NATS, or RabbitMQ for
  multi-process / multi-node deployments. The current in-process
  implementation would become the default "local" backend.
- **Heartbeat service** — Proactive health monitoring with configurable
  intervals, component health checks, and missed-heartbeat callbacks.
- **Channel middleware** — Pluggable pre/post-processing pipeline for
  inbound and outbound messages (rate limiting, logging, transforms).
- **Session TTL & eviction** — Automatic expiry of idle sessions with
  configurable max-message limits.
