"""Unit tests for gateway.bus module."""

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
        assert bus.inbound_size == 0, f"expect inbound queue starts empty as 0, got size {bus.inbound_size}"
        assert bus.outbound_size == 0, f"expect outbound queue starts empty as 0, got size {bus.outbound_size}"
        assert bus._subscribers == {}, f"expect MessageBus starts with no registered topic subscribers as {{}}, got {bus._subscribers}"


class TestMessageBusInbound:
    """Test inbound queue operations."""

    async def test_publish_and_consume_inbound(self):
        bus = MessageBus()
        msg = _make_inbound("hello")
        await bus.publish_inbound(msg)

        assert bus.inbound_size == 1, f"expect publish_inbound increments inbound queue size to one for single published message as 1, got {bus.inbound_size}"
        consumed = await bus.consume_inbound()
        assert consumed is msg, f"expect consume_inbound returns the same inbound message instance that was published as {msg}, got {consumed}"
        assert consumed.content == "hello", f"expect consume_inbound preserves inbound message content payload as 'hello', got {consumed.content}"
        assert bus.inbound_size == 0, f"expect inbound queue empty after consuming one published message as 0, got size {bus.inbound_size}"

    async def test_inbound_fifo_order(self):
        bus = MessageBus()
        m1 = _make_inbound("first")
        m2 = _make_inbound("second")
        m3 = _make_inbound("third")

        await bus.publish_inbound(m1)
        await bus.publish_inbound(m2)
        await bus.publish_inbound(m3)

        first_consumed = await bus.consume_inbound()
        assert first_consumed.content == "first", f"expect inbound queue consumption preserves FIFO order for first item as 'first', got {first_consumed.content}"
        second_consumed = await bus.consume_inbound()
        assert second_consumed.content == "second", f"expect inbound queue consumption preserves FIFO order for second item as 'second', got {second_consumed.content}"
        third_consumed = await bus.consume_inbound()
        assert third_consumed.content == "third", f"expect inbound queue consumption preserves FIFO order for third item as 'third', got {third_consumed.content}"

    async def test_publish_inbound_triggers_subscriber(self):
        bus = MessageBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("inbound", handler)
        msg = _make_inbound()
        await bus.publish_inbound(msg)

        received_count = len(received)
        assert received_count == 1, f"expect publish_inbound triggers exactly one subscriber callback invocation as 1, got {received_count}"
        assert received[0] is msg, f"expect inbound subscriber receives original published message instance as {msg}, got {received[0]}"


class TestMessageBusOutbound:
    """Test outbound queue operations."""

    async def test_publish_and_consume_outbound(self):
        bus = MessageBus()
        msg = _make_outbound("reply")
        await bus.publish_outbound(msg)

        assert bus.outbound_size == 1, f"expect publish_outbound increments outbound queue size to one for single published message as 1, got {bus.outbound_size}"
        consumed = await bus.consume_outbound()
        assert consumed is msg, f"expect consume_outbound returns the same outbound message instance that was published as {msg}, got {consumed}"
        assert consumed.content == "reply", f"expect consume_outbound preserves outbound message content payload as 'reply', got {consumed.content}"
        assert bus.outbound_size == 0, f"expect outbound queue empty after consuming one published message as 0, got size {bus.outbound_size}"

    async def test_outbound_fifo_order(self):
        bus = MessageBus()
        m1 = _make_outbound("a")
        m2 = _make_outbound("b")
        await bus.publish_outbound(m1)
        await bus.publish_outbound(m2)

        first_consumed = await bus.consume_outbound()
        assert first_consumed.content == "a", f"expect outbound queue consumption preserves FIFO order for first item as 'a', got {first_consumed.content}"
        second_consumed = await bus.consume_outbound()
        assert second_consumed.content == "b", f"expect outbound queue consumption preserves FIFO order for second item as 'b', got {second_consumed.content}"

    async def test_publish_outbound_triggers_subscriber(self):
        bus = MessageBus()
        received = []

        async def handler(msg):
            received.append(msg)

        bus.subscribe("outbound", handler)
        msg = _make_outbound()
        await bus.publish_outbound(msg)

        received_count = len(received)
        assert received_count == 1, f"expect publish_outbound triggers exactly one subscriber callback invocation as 1, got {received_count}"
        assert received[0] is msg, f"expect outbound subscriber receives original published message instance as {msg}, got {received[0]}"


class TestMessageBusPubSub:
    """Test topic-based pub/sub."""

    async def test_subscribe_and_emit(self):
        bus = MessageBus()
        received = []

        async def handler(data):
            received.append(data)

        bus.subscribe("my_topic", handler)
        await bus.emit("my_topic", {"key": "val"})

        assert received == [{"key": "val"}], f"expect emit delivers payload to subscribers of matching topic as [{'key': 'val'}], got {received}"

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

        assert log1 == [42], f"expect first subscriber receives emitted payload for shared topic as [42], got {log1}"
        assert log2 == [42], f"expect second subscriber receives emitted payload for shared topic as [42], got {log2}"

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
        assert received == [1], f"expect subscriber receives first emitted payload before unsubscribe as [1], got {received}"

        bus.unsubscribe("t", handler)
        await bus.emit("t", 2)
        assert received == [1], f"expect unsubscribed handler does not receive subsequent emit payloads as [1], got {received}"  # Should NOT receive second emit

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
        assert received == ["x"], f"expect removing non-registered handler keeps existing subscribers active as ['x'], got {received}"  # h1 still active

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

        assert received == ["val"], f"expect subscriber exceptions do not block execution of remaining subscribers as ['val'], got {received}"

    async def test_emit_with_none_data(self):
        bus = MessageBus()
        received = []

        async def handler(data):
            received.append(data)

        bus.subscribe("t", handler)
        await bus.emit("t", None)
        assert received == [None], f"expect emit propagates None payload to subscribers as [None], got {received}"

    async def test_emit_with_no_data(self):
        bus = MessageBus()
        received = []

        async def handler(data):
            received.append(data)

        bus.subscribe("t", handler)
        await bus.emit("t")
        assert received == [None], f"expect [None], got {received}"


class TestMessageBusIntrospection:
    """Test size properties."""

    async def test_inbound_size(self):
        bus = MessageBus()
        assert bus.inbound_size == 0, f"expect inbound queue starts at size 0, got {bus.inbound_size}"
        await bus.publish_inbound(_make_inbound())
        assert bus.inbound_size == 1, f"expect inbound queue size increments to 1 after first publish_inbound call, got {bus.inbound_size}"
        await bus.publish_inbound(_make_inbound())
        assert bus.inbound_size == 2, f"expect inbound queue size increments to 2 after second publish_inbound call, got {bus.inbound_size}"
        await bus.consume_inbound()
        assert bus.inbound_size == 1, f"expect inbound queue size decrements to 1 after consuming one of two messages, got {bus.inbound_size}"

    async def test_outbound_size(self):
        bus = MessageBus()
        assert bus.outbound_size == 0, f"expect outbound queue starts at size 0, got {bus.outbound_size}"
        await bus.publish_outbound(_make_outbound())
        assert bus.outbound_size == 1, f"expect outbound queue size increments to 1 after first publish_outbound call, got {bus.outbound_size}"
        await bus.consume_outbound()
        assert bus.outbound_size == 0, f"expect outbound queue returns to size 0 after consume, got {bus.outbound_size}"
