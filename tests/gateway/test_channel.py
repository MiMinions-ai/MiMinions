"""Unit tests for gateway.channel module."""
import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock
from dataclasses import dataclass

from miminions.core.gateway.bus import MessageBus
from miminions.core.gateway.channel import BaseChannel, ChannelManager
from miminions.core.gateway.events import InboundMessage, OutboundMessage


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
        assert ch.config is cfg
        assert ch.bus is bus
        assert ch.is_running is False

    def test_custom_name(self):
        ch = EchoChannel(DummyConfig(), MessageBus())
        assert ch.name == "echo"


class TestBaseChannelIsAllowed:
    """Test is_allowed access control."""

    def test_wildcard_allows_all(self):
        ch = EchoChannel(DummyConfig(allow_from=["*"]), MessageBus())
        assert ch.is_allowed("anyone") is True

    def test_specific_id_allowed(self):
        ch = EchoChannel(DummyConfig(allow_from=["u1", "u2"]), MessageBus())
        assert ch.is_allowed("u1") is True
        assert ch.is_allowed("u2") is True
        assert ch.is_allowed("u3") is False

    def test_empty_allow_from_denies_all(self):
        ch = EchoChannel(DummyConfig(allow_from=[]), MessageBus())
        assert ch.is_allowed("anyone") is False

    def test_no_allow_from_attribute_denies_all(self):
        """Config without allow_from attribute should deny."""
        ch = EchoChannel(object(), MessageBus())
        assert ch.is_allowed("x") is False

    def test_sender_id_cast_to_str(self):
        ch = EchoChannel(DummyConfig(allow_from=["42"]), MessageBus())
        assert ch.is_allowed(42) is True


class TestBaseChannelHandleMessage:
    """Test _handle_message method."""

    async def test_handle_message_publishes_to_bus(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["*"]), bus)

        await ch._handle_message("u1", "c1", "hello")

        assert bus.inbound_size == 1
        msg = await bus.consume_inbound()
        assert msg.channel == "echo"
        assert msg.sender_id == "u1"
        assert msg.chat_id == "c1"
        assert msg.content == "hello"

    async def test_handle_message_with_media_and_metadata(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["*"]), bus)

        await ch._handle_message(
            "u1", "c1", "img",
            media=["url1"],
            metadata={"k": "v"},
        )

        msg = await bus.consume_inbound()
        assert msg.media == ["url1"]
        assert msg.metadata == {"k": "v"}

    async def test_handle_message_with_session_key(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["*"]), bus)

        await ch._handle_message("u1", "c1", "hi", session_key="custom-key")

        msg = await bus.consume_inbound()
        assert msg.session_key == "custom-key"

    async def test_handle_message_denied_sender_not_published(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["allowed_user"]), bus)

        await ch._handle_message("denied_user", "c1", "hi")

        assert bus.inbound_size == 0

    async def test_handle_message_defaults_media_and_metadata(self):
        bus = MessageBus()
        ch = EchoChannel(DummyConfig(allow_from=["*"]), bus)

        await ch._handle_message("u1", "c1", "")

        msg = await bus.consume_inbound()
        assert msg.media == []
        assert msg.metadata == {}


class TestBaseChannelLifecycle:
    """Test start/stop and is_running."""

    async def test_start_stop(self):
        ch = EchoChannel(DummyConfig(), MessageBus())
        assert ch.is_running is False

        await ch.start()
        assert ch.is_running is True

        await ch.stop()
        assert ch.is_running is False


# ── ChannelManager tests ─────────────────────────────────────────────


class TestChannelManagerInit:
    def test_init(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        assert mgr.bus is bus
        assert mgr.channels == {}
        assert mgr._dispatch_task is None


class TestChannelManagerRegister:
    def test_register_and_get(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        ch = EchoChannel(DummyConfig(), bus)

        mgr.register(ch)
        assert mgr.get_channel("echo") is ch
        assert mgr.enabled_channels == ["echo"]

    def test_unregister(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        ch = EchoChannel(DummyConfig(), bus)

        mgr.register(ch)
        mgr.unregister("echo")
        assert mgr.get_channel("echo") is None
        assert mgr.enabled_channels == []

    def test_unregister_nonexistent(self):
        mgr = ChannelManager(MessageBus())
        mgr.unregister("nope")  # Should not raise

    def test_get_channel_nonexistent(self):
        mgr = ChannelManager(MessageBus())
        assert mgr.get_channel("nope") is None


class TestChannelManagerStatus:
    def test_get_status_empty(self):
        mgr = ChannelManager(MessageBus())
        assert mgr.get_status() == {}

    async def test_get_status_with_channels(self):
        bus = MessageBus()
        mgr = ChannelManager(bus)
        ch = EchoChannel(DummyConfig(), bus)
        mgr.register(ch)

        status = mgr.get_status()
        assert status == {"echo": {"enabled": True, "running": False}}

        await ch.start()
        status = mgr.get_status()
        assert status == {"echo": {"enabled": True, "running": True}}


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

        assert ch.is_running is True

        await mgr.stop_all()
        start_task.cancel()
        try:
            await start_task
        except asyncio.CancelledError:
            pass

        assert ch.is_running is False

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

        assert good.is_running is True

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

        assert len(sent) == 1
        assert sent[0].content == "reply"

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
