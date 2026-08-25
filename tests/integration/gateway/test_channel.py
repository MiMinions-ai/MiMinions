"""Unit tests for gateway.channel module."""
import asyncio
from dataclasses import dataclass

from miminions.core.gateway.bus import MessageBus
from miminions.core.gateway.channel import BaseChannel, ChannelManager
from miminions.core.gateway.events import OutboundMessage

# ── Helpers ──────────────────────────────────────────────────────────


@dataclass
class DummyConfig:
    allow_from: list[str] | None = None

    def __post_init__(self):
        if self.allow_from is None:
            self.allow_from = ["*"]


class EchoChannel(BaseChannel):
    """Minimal concrete channel for testing."""

    name = "echo"

    async def start(self) -> None:
        self._running = True

    async def stop(self) -> None:
        self._running = False

    async def send(self, msg: OutboundMessage) -> None:
        pass  # No-op


class FailingChannel(BaseChannel):
    """Channel that fails to start."""

    name = "failing"

    async def start(self) -> None:
        raise RuntimeError("startup failure")

    async def stop(self) -> None:
        raise RuntimeError("stop failure")

    async def send(self, msg: OutboundMessage) -> None:
        raise RuntimeError("send failure")


# ── BaseChannel tests ────────────────────────────────────────────────


class TestBaseChannelInit:
    """Test BaseChannel initialization."""

    def test_attributes(self):
        bus = MessageBus()
        cfg = DummyConfig()
        ch = EchoChannel(cfg, bus)
        assert ch.config is cfg, f"expect cfg as {cfg}, got {ch.config}"
        assert ch.bus is bus, f"expect bus as {bus}, got {ch.bus}"
        assert ch.is_running is False, f"expect newly created channel starts in non-running state before lifecycle start as False, got {ch.is_running}"

    def test_custom_name(self):
        ch = EchoChannel(DummyConfig(), MessageBus())
        assert ch.name == "echo", f"expect EchoChannel exposes static channel name identifier used for routing as 'echo', got {ch.name}"


class TestBaseChannelIsAllowed:
    """Test is_allowed access control."""

    def test_wildcard_allows_all(self):
        ch = EchoChannel(DummyConfig(allow_from=["*"]), MessageBus())
        anyone_allowed = ch.is_allowed("anyone")
        assert anyone_allowed is True, f"expect wildcard allow_from grants access to any sender id as True, got {anyone_allowed}"

    def test_specific_id_allowed(self):
        ch = EchoChannel(DummyConfig(allow_from=["u1", "u2"]), MessageBus())
        u1_allowed = ch.is_allowed("u1")
        assert u1_allowed is True, f"expect sender id listed in allow_from is accepted by access check as True, got {u1_allowed}"
        u2_allowed = ch.is_allowed("u2")
        assert u2_allowed is True, f"expect second sender id listed in allow_from is accepted by access check as True, got {u2_allowed}"
        u3_allowed = ch.is_allowed("u3")
        assert u3_allowed is False, f"expect sender id absent from allow_from is rejected by access check as False, got {u3_allowed}"

    def test_empty_allow_from_denies_all(self):
        ch = EchoChannel(DummyConfig(allow_from=[]), MessageBus())
        anyone_allowed = ch.is_allowed("anyone")
        assert anyone_allowed is False, f"expect empty allow_from list denies all senders by default as False, got {anyone_allowed}"

    def test_no_allow_from_attribute_denies_all(self):
        """Config without allow_from attribute should deny."""
        ch = EchoChannel(object(), MessageBus())
        x_allowed = ch.is_allowed("x")
        assert x_allowed is False, f"expect config without allow_from attribute denies sender access checks as False, got {x_allowed}"

    def test_sender_id_cast_to_str(self):
        ch = EchoChannel(DummyConfig(allow_from=["42"]), MessageBus())
        sender_allowed = ch.is_allowed(42)
        assert sender_allowed is True, f"expect non-string sender ids are cast to string before allow_from membership check as True, got {sender_allowed}"


class TestBaseChannelHandleMessage:
    """Test _handle_message method."""

    async def test_handle_message_publishes_to_bus(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["*"]), bus)

        await ch._handle_message("u1", "c1", "hello")

        assert bus.inbound_size == 1, f"expect _handle_message publishes exactly one inbound message for one handled input as 1, got {bus.inbound_size}"
        msg = await bus.consume_inbound()
        assert msg.channel == "echo", f"expect _handle_message stamps inbound event with originating channel name as 'echo', got {msg.channel}"
        assert msg.sender_id == "u1", f"expect _handle_message preserves sender id in published inbound event as 'u1', got {msg.sender_id}"
        assert msg.chat_id == "c1", f"expect _handle_message preserves chat id in published inbound event as 'c1', got {msg.chat_id}"
        assert msg.content == "hello", f"expect _handle_message preserves text content in published inbound event as 'hello', got {msg.content}"

    async def test_handle_message_with_media_and_metadata(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["*"]), bus)

        await ch._handle_message(
            "u1", "c1", "img",
            media=["url1"],
            metadata={"k": "v"},
        )

        msg = await bus.consume_inbound()
        assert msg.media == ["url1"], f"expect _handle_message forwards media payload as ['url1'] in published inbound message, got {msg.media}"
        assert msg.metadata == {"k": "v"}, f"expect _handle_message forwards metadata payload as {{'k': 'v'}} in published inbound message, got {msg.metadata}"

    async def test_handle_message_with_session_key(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["*"]), bus)

        await ch._handle_message("u1", "c1", "hi", session_key="custom-key")

        msg = await bus.consume_inbound()
        assert msg.session_key == "custom-key", f"expect _handle_message forwards explicit session_key into inbound event metadata as 'custom-key', got {msg.session_key}"

    async def test_handle_message_denied_sender_not_published(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["allowed_user"]), bus)

        await ch._handle_message("denied_user", "c1", "hi")

        assert bus.inbound_size == 0, f"expect denied sender message not published to inbound queue as 0, got queue size {bus.inbound_size}"

    async def test_handle_message_defaults_media_and_metadata(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["*"]), bus)

        await ch._handle_message("u1", "c1", "")

        msg = await bus.consume_inbound()
        assert msg.media == [], f"expect _handle_message defaults media field to empty list when omitted as [], got {msg.media}"
        assert msg.metadata == {}, f"expect _handle_message defaults metadata field to empty mapping when omitted as {{}}, got {msg.metadata}"


class TestBaseChannelLifecycle:
    """Test start/stop and is_running."""

    async def test_start_stop(self):
        ch = EchoChannel(DummyConfig(), MessageBus())
        assert ch.is_running is False, f"expect channel is not running before start is called as False, got {ch.is_running}"

        await ch.start()
        assert ch.is_running is True, f"expect channel is running after start lifecycle call as True, got {ch.is_running}"

        await ch.stop()
        assert ch.is_running is False, f"expect channel returns to non-running state after stop lifecycle call as False, got {ch.is_running}"


# ── ChannelManager tests ─────────────────────────────────────────────


class TestChannelManagerInit:
    def test_init(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        assert mgr.bus is bus, f"expect bus as {bus}, got {mgr.bus}"
        assert mgr.channels == {}, f"expect ChannelManager starts with no registered channels as {{}}, got {mgr.channels}"
        assert mgr._dispatch_task is None, f"expect ChannelManager starts without active outbound dispatch task as None, got {mgr._dispatch_task}"


class TestChannelManagerRegister:
    def test_register_and_get(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        ch = EchoChannel(DummyConfig(), bus)

        mgr.register(ch)
        echo_channel = mgr.get_channel("echo")
        assert echo_channel is ch, f"expect ch as {ch}, got {echo_channel}"
        assert mgr.enabled_channels == ["echo"], f"expect ['echo'], got {mgr.enabled_channels}"

    def test_unregister(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        ch = EchoChannel(DummyConfig(), bus)

        mgr.register(ch)
        mgr.unregister("echo")
        echo_channel = mgr.get_channel("echo")
        assert echo_channel is None, f"expect get_channel returns None after channel is unregistered, got {echo_channel}"
        assert mgr.enabled_channels == [], f"expect enabled_channels is empty after unregister removes last channel as [], got {mgr.enabled_channels}"

    def test_unregister_nonexistent(self):
        mgr = ChannelManager(MessageBus())
        mgr.unregister("nope")  # Should not raise

    def test_get_channel_nonexistent(self):
        mgr = ChannelManager(MessageBus())
        missing_channel = mgr.get_channel("nope")
        assert missing_channel is None, f"expect get_channel returns None for unknown channel name lookup, got {missing_channel}"


class TestChannelManagerStatus:
    def test_get_status_empty(self):
        mgr = ChannelManager(MessageBus())
        status = mgr.get_status()
        assert status == {}, f"expect get_status returns empty mapping when no channels are registered as {{}}, got {status}"

    async def test_get_status_with_channels(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        ch = EchoChannel(DummyConfig(), bus)
        mgr.register(ch)

        status = mgr.get_status()
        assert status == {"echo": {"enabled": True, "running": False}}, f"expect get_status reports registered echo channel state as {{'echo': {{'enabled': True, 'running': False}}}}, got {status}"

        await ch.start()
        status = mgr.get_status()
        assert status == {"echo": {"enabled": True, "running": True}}, f"expect get_status reports running echo channel state as {{'echo': {{'enabled': True, 'running': True}}}}, got {status}"


class TestChannelManagerStartStop:
    async def test_start_all_no_channels(self):
        """start_all with no channels should return without error."""
        mgr = ChannelManager(MessageBus())
        await mgr.start_all()

    async def test_stop_all_no_dispatch_task(self):
        """stop_all with no dispatch task should not error."""
        mgr = ChannelManager(MessageBus())
        await mgr.stop_all()

    async def test_start_and_stop_channel(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        ch = EchoChannel(DummyConfig(), bus)
        mgr.register(ch)

        # start_all runs as a long-running task, so run briefly then stop
        start_task = asyncio.create_task(mgr.start_all())
        await asyncio.sleep(0.05)

        assert ch.is_running is True, f"expect start_all starts registered channels before dispatch loop runs as True, got {ch.is_running}"

        await mgr.stop_all()
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        assert ch.is_running is False, f"expect stop_all stops running channels before test teardown as False, got {ch.is_running}"

    async def test_start_failing_channel(self):
        """A failing channel should not crash the manager."""
        bus = MessageBus()
        mgr = ChannelManager(bus)
        good = EchoChannel(DummyConfig(), bus)
        bad = FailingChannel(DummyConfig(), bus)
        mgr.register(good)
        mgr.register(bad)

        start_task = asyncio.create_task(mgr.start_all())
        await asyncio.sleep(0.05)

        assert good.is_running is True, f"expect manager continues starting healthy channels even when one channel fails startup as True, got {good.is_running}"

        await mgr.stop_all()
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    async def test_stop_all_with_failing_channel(self):
        """stop_all should handle channel stop errors gracefully."""
        bus = MessageBus()
        mgr = ChannelManager(bus)
        bad = FailingChannel(DummyConfig(), bus)
        mgr.register(bad)

        # Stopping a failing channel should not raise
        await mgr.stop_all()


class TestChannelManagerDispatch:
    async def test_outbound_dispatch(self):
        """Outbound messages should be dispatched to the correct channel."""
        bus = MessageBus()
        mgr = ChannelManager(bus)

        sent = []

        class RecordChannel(BaseChannel):
            name = "record"

            async def start(self):
                self._running = True

            async def stop(self):
                self._running = False

            async def send(self, msg):
                sent.append(msg)

        ch = RecordChannel(DummyConfig(), bus)
        mgr.register(ch)

        start_task = asyncio.create_task(mgr.start_all())
        await asyncio.sleep(0.05)

        out_msg = OutboundMessage(channel="record", chat_id="c1", content="reply")
        await bus.publish_outbound(out_msg)
        await asyncio.sleep(0.1)

        sent_count = len(sent)
        assert sent_count == 1, f"expect outbound dispatcher sends one message to registered matching channel for one outbound publish as 1, got {sent_count}"
        assert sent[0].content == "reply", f"expect outbound dispatcher sends message payload to matching registered channel as 'reply', got {sent[0].content}"

        await mgr.stop_all()
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    async def test_outbound_unknown_channel(self):
        """Messages to an unknown channel should be logged and skipped."""
        bus = MessageBus()
        mgr = ChannelManager(bus)
        ch = EchoChannel(DummyConfig(), bus)
        mgr.register(ch)

        start_task = asyncio.create_task(mgr.start_all())
        await asyncio.sleep(0.05)

        out_msg = OutboundMessage(channel="nonexistent", chat_id="c", content="x")
        await bus.publish_outbound(out_msg)
        await asyncio.sleep(0.1)

        # Should not crash
        await mgr.stop_all()
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

    async def test_outbound_send_error(self):
        """Send errors should be logged, not crash the dispatcher."""
        bus = MessageBus()
        mgr = ChannelManager(bus)
        bad = FailingChannel(DummyConfig(), bus)
        mgr.register(bad)

        start_task = asyncio.create_task(mgr.start_all())
        await asyncio.sleep(0.05)

        out_msg = OutboundMessage(channel="failing", chat_id="c", content="x")
        await bus.publish_outbound(out_msg)
        await asyncio.sleep(0.1)

        await mgr.stop_all()
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass
