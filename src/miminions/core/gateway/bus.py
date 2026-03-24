"""In-process async message bus for decoupled channel-agent communication.

Provides a pub/sub event-driven architecture using asyncio queues.
Channels push messages to the inbound queue, and the agent processes
them and pushes responses to the outbound queue. Subscribers can
listen to named topics for event-driven workflows.
"""

import asyncio
import logging
from typing import Any, Callable, Coroutine

from .events import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)

# Type alias for async subscriber callbacks
Subscriber = Callable[..., Coroutine[Any, Any, None]]


class MessageBus:
    """
    Async message bus that decouples chat channels from the agent core.

    Two built-in queues handle the primary inbound/outbound message flow.
    An optional topic-based pub/sub layer allows components to react to
    arbitrary events without direct coupling.
    """

    _DEFAULT_MAXSIZE = 1000

    def __init__(self, maxsize: int = _DEFAULT_MAXSIZE) -> None:
        self.inbound: asyncio.Queue[InboundMessage] = asyncio.Queue(maxsize=maxsize)
        self.outbound: asyncio.Queue[OutboundMessage] = asyncio.Queue(maxsize=maxsize)
        self._subscribers: dict[str, list[Subscriber]] = {}

    # ── Inbound (channel → agent) ────────────────────────────────────

    async def publish_inbound(self, msg: InboundMessage) -> None:
        """Publish a message from a channel to the agent."""
        await self.inbound.put(msg)
        await self._notify("inbound", msg)

    async def consume_inbound(self) -> InboundMessage:
        """Consume the next inbound message (blocks until available)."""
        return await self.inbound.get()

    # ── Outbound (agent → channel) ───────────────────────────────────

    async def publish_outbound(self, msg: OutboundMessage) -> None:
        """Publish a response from the agent to channels."""
        await self.outbound.put(msg)
        await self._notify("outbound", msg)

    async def consume_outbound(self) -> OutboundMessage:
        """Consume the next outbound message (blocks until available)."""
        return await self.outbound.get()

    # ── Topic-based pub/sub ──────────────────────────────────────────

    def subscribe(self, topic: str, handler: Subscriber) -> None:
        """Register an async handler for a named topic."""
        if topic not in self._subscribers:
            self._subscribers[topic] = []
        self._subscribers[topic].append(handler)

    def unsubscribe(self, topic: str, handler: Subscriber) -> None:
        """Remove a handler from a topic."""
        if topic in self._subscribers:
            self._subscribers[topic] = [
                h for h in self._subscribers[topic] if h is not handler
            ]

    async def emit(self, topic: str, data: Any = None) -> None:
        """Emit an event on a named topic, notifying all subscribers."""
        await self._notify(topic, data)

    async def _notify(self, topic: str, data: Any) -> None:
        """Invoke all subscribers for a given topic."""
        for handler in self._subscribers.get(topic, []):
            try:
                await handler(data)
            except Exception:
                logger.exception("Error in subscriber for topic '%s'", topic)

    # ── Introspection ────────────────────────────────────────────────

    @property
    def inbound_size(self) -> int:
        """Number of pending inbound messages."""
        return self.inbound.qsize()

    @property
    def outbound_size(self) -> int:
        """Number of pending outbound messages."""
        return self.outbound.qsize()
