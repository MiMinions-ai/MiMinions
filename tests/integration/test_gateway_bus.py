"""Unit tests for gateway.bus module."""
import pytest
import asyncio

from miminions.core.gateway.bus import MessageBus
from miminions.core.gateway.events import InboundMessage, OutboundMessage


def _make_inbound(content="hi", channel="test", sender="u1", chat="c1"):
    return InboundMessage(
        channel=channel, sender_id=sender, chat_id=chat, content=content
    )


def _make_outbound(content="ok", channel="test", chat="c1"):
    return OutboundMessage(channel=channel, chat_id=chat, content=content)


class TestMessageBusInit:
    """Test MessageBus initialization."""

    def test_initial_state(self):
        bus = MessageBus()
        assert bus.inbound_size == 0
        assert bus.outbound_size == 0
        assert bus._subscribers == {}


class TestMessageBusInbound:
    """Test inbound queue operations."""

    async def test_publish_and_consume_inbound(self):
        bus = MessageBus()
        msg = _make_inbound("hello")
        await bus.publish_inbound(msg)

        assert bus.inbound_size == 1
        consumed = await bus.consume_inbound()
        assert consumed is msg
        assert consumed.content == "hello"
        assert bus.inbound_size == 0

    async def test_inbound_fifo_order(self):
        bus = MessageBus()
        m1 = _make_inbound("first")
        m2 = _make_inbound("second")
        m3 = _make_inbound("third")

        await bus.publish_inbound(m1)
        await bus.publish_inbound(m2)
        await bus.publish_inbound(m3)

        assert (await bus.consume_inbound()).content == "first"
        assert (await bus.consume_inbound()).content == "second"
        assert (await bus.consume_inbound()).content == "third"

    async def test_publish_inbound_triggers_subscriber(self):
        bus = MessageBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("inbound", handler)
        msg = _make_inbound()
        await bus.publish_inbound(msg)

        assert len(received) == 1
        assert received[0] is msg


class TestMessageBusOutbound:
    """Test outbound queue operations."""

    async def test_publish_and_consume_outbound(self):
        bus = MessageBus()
        msg = _make_outbound("reply")
        await bus.publish_outbound(msg)

        assert bus.outbound_size == 1
        consumed = await bus.consume_outbound()
        assert consumed is msg
        assert consumed.content == "reply"
        assert bus.outbound_size == 0

    async def test_outbound_fifo_order(self):
        bus = MessageBus()
        m1 = _make_outbound("a")
        m2 = _make_outbound("b")
        await bus.publish_outbound(m1)
        await bus.publish_outbound(m2)

        assert (await bus.consume_outbound()).content == "a"
        assert (await bus.consume_outbound()).content == "b"

    async def test_publish_outbound_triggers_subscriber(self):
        bus = MessageBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("outbound", handler)
        msg = _make_outbound()
        await bus.publish_outbound(msg)

        assert len(received) == 1
        assert received[0] is msg


class TestMessageBusPubSub:
    """Test topic-based pub/sub."""

    async def test_subscribe_and_emit(self):
        bus = MessageBus()
        received = []

        async def handler(data):
            received.append(data)

        bus.subscribe("my_topic", handler)
        await bus.emit("my_topic", {"key": "val"})

        assert received == [{"key": "val"}]

    async def test_multiple_subscribers_same_topic(self):
        bus = MessageBus()
        log1, log2 = [], []

        async def h1(data):
            log1.append(data)

        async def h2(data):
            log2.append(data)

        bus.subscribe("topic", h1)
        bus.subscribe("topic", h2)
        await bus.emit("topic", 42)

        assert log1 == [42]
        assert log2 == [42]

    async def test_emit_no_subscribers(self):
        """Emitting to a topic with no subscribers should not error."""
        bus = MessageBus()
        await bus.emit("nobody_listens", "data")

    async def test_unsubscribe(self):
        bus = MessageBus()
        received = []

        async def handler(data):
            received.append(data)

        bus.subscribe("t", handler)
        await bus.emit("t", 1)
        assert received == [1]

        bus.unsubscribe("t", handler)
        await bus.emit("t", 2)
        assert received == [1]  # Should NOT receive second emit

    async def test_unsubscribe_nonexistent_topic(self):
        """Unsubscribing from a topic that doesn't exist should not error."""
        bus = MessageBus()

        async def handler(data):
            pass

        bus.unsubscribe("nonexistent", handler)

    async def test_unsubscribe_nonexistent_handler(self):
        """Unsubscribing a handler not in the list should not error."""
        bus = MessageBus()
        received = []

        async def h1(data):
            received.append(data)

        async def h2(data):
            pass

        bus.subscribe("t", h1)
        bus.unsubscribe("t", h2)  # h2 was never subscribed
        await bus.emit("t", "x")
        assert received == ["x"]  # h1 still active

    async def test_subscriber_exception_logged_and_continues(self):
        """A failing subscriber should not prevent other subscribers from running."""
        bus = MessageBus()
        received = []

        async def bad_handler(data):
            raise RuntimeError("boom")

        async def good_handler(data):
            received.append(data)

        bus.subscribe("t", bad_handler)
        bus.subscribe("t", good_handler)
        await bus.emit("t", "val")

        assert received == ["val"]

    async def test_emit_with_none_data(self):
        bus = MessageBus()
        received = []

        async def handler(data):
            received.append(data)

        bus.subscribe("t", handler)
        await bus.emit("t", None)
        assert received == [None]

    async def test_emit_with_no_data(self):
        bus = MessageBus()
        received = []

        async def handler(data):
            received.append(data)

        bus.subscribe("t", handler)
        await bus.emit("t")
        assert received == [None]


class TestMessageBusIntrospection:
    """Test size properties."""

    async def test_inbound_size(self):
        bus = MessageBus()
        assert bus.inbound_size == 0
        await bus.publish_inbound(_make_inbound())
        assert bus.inbound_size == 1
        await bus.publish_inbound(_make_inbound())
        assert bus.inbound_size == 2
        await bus.consume_inbound()
        assert bus.inbound_size == 1

    async def test_outbound_size(self):
        bus = MessageBus()
        assert bus.outbound_size == 0
        await bus.publish_outbound(_make_outbound())
        assert bus.outbound_size == 1
        await bus.consume_outbound()
        assert bus.outbound_size == 0
