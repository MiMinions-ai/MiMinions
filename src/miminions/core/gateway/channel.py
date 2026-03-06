"""Abstract base channel interface and channel manager for chat platforms.

Mirrors the nanobot channel abstraction: each channel (Telegram, Discord,
WebSocket, etc.) implements BaseChannel and integrates with the gateway
message bus. The ChannelManager coordinates lifecycle and outbound routing.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from typing import Any

from .bus import MessageBus
from .events import InboundMessage, OutboundMessage

logger = logging.getLogger(__name__)


class BaseChannel(ABC):
    """
    Abstract base class for chat channel implementations.

    Each channel should implement this interface to integrate with the
    gateway message bus.  Subclasses must override ``start``, ``stop``,
    and ``send``.
    """

    name: str = "base"

    def __init__(self, config: Any, bus: MessageBus) -> None:
        """
        Initialize the channel.

        Args:
            config: Channel-specific configuration.
            bus: The message bus for communication.
        """
        self.config = config
        self.bus = bus
        self._running = False

    @abstractmethod
    async def start(self) -> None:
        """
        Start the channel and begin listening for messages.

        This should be a long-running async task that:
        1. Connects to the chat platform
        2. Listens for incoming messages
        3. Forwards messages to the bus via ``_handle_message``
        """

    @abstractmethod
    async def stop(self) -> None:
        """Stop the channel and clean up resources."""

    @abstractmethod
    async def send(self, msg: OutboundMessage) -> None:
        """Send a message through this channel."""

    def is_allowed(self, sender_id: str) -> bool:
        """Check if *sender_id* is permitted by the allow list.

        An empty ``allow_from`` list denies all senders.
        A list containing ``"*"`` allows everyone.
        """
        allow_list: list[str] = getattr(self.config, "allow_from", [])
        if not allow_list:
            logger.warning("%s: allow_from is empty — all access denied", self.name)
            return False
        if "*" in allow_list:
            return True
        return str(sender_id) in allow_list

    async def _handle_message(
        self,
        sender_id: str,
        chat_id: str,
        content: str,
        media: list[str] | None = None,
        metadata: dict[str, Any] | None = None,
        session_key: str | None = None,
    ) -> None:
        """Handle an incoming message from the chat platform.

        Checks permissions and forwards the message to the bus.
        """
        if not self.is_allowed(sender_id):
            logger.warning(
                "Access denied for sender %s on channel %s.",
                sender_id,
                self.name,
            )
            return

        msg = InboundMessage(
            channel=self.name,
            sender_id=str(sender_id),
            chat_id=str(chat_id),
            content=content,
            media=media or [],
            metadata=metadata or {},
            session_key_override=session_key,
        )
        await self.bus.publish_inbound(msg)

    @property
    def is_running(self) -> bool:
        """Check if the channel is running."""
        return self._running


class ChannelManager:
    """
    Manages chat channels and coordinates message routing.

    Responsibilities:
    - Register and track channel instances
    - Start/stop channels
    - Route outbound messages to the correct channel
    """

    def __init__(self, bus: MessageBus) -> None:
        self.bus = bus
        self.channels: dict[str, BaseChannel] = {}
        self._dispatch_task: asyncio.Task | None = None

    def register(self, channel: BaseChannel) -> None:
        """Register a channel by its name."""
        self.channels[channel.name] = channel

    def unregister(self, name: str) -> None:
        """Remove a channel by name."""
        self.channels.pop(name, None)

    async def start_all(self) -> None:
        """Start all registered channels and the outbound dispatcher."""
        if not self.channels:
            logger.warning("No channels registered")
            return

        self._dispatch_task = asyncio.create_task(self._dispatch_outbound())

        tasks = []
        for name, channel in self.channels.items():
            logger.info("Starting %s channel...", name)
            tasks.append(asyncio.create_task(self._start_channel(name, channel)))
        await asyncio.gather(*tasks, return_exceptions=True)

    async def stop_all(self) -> None:
        """Stop all channels and the dispatcher."""
        logger.info("Stopping all channels...")

        if self._dispatch_task:
            self._dispatch_task.cancel()
            try:
                await self._dispatch_task
            except asyncio.CancelledError:
                pass

        for name, channel in self.channels.items():
            try:
                await channel.stop()
                logger.info("Stopped %s channel", name)
            except Exception:
                logger.exception("Error stopping %s", name)

    async def _start_channel(self, name: str, channel: BaseChannel) -> None:
        """Start a single channel, logging any errors."""
        try:
            await channel.start()
        except Exception:
            logger.exception("Failed to start channel %s", name)

    async def _dispatch_outbound(self) -> None:
        """Dispatch outbound messages to the appropriate channel."""
        while True:
            try:
                msg = await asyncio.wait_for(
                    self.bus.consume_outbound(),
                    timeout=1.0,
                )
                channel = self.channels.get(msg.channel)
                if channel:
                    try:
                        await channel.send(msg)
                    except Exception:
                        logger.exception("Error sending to %s", msg.channel)
                else:
                    logger.warning("Unknown channel: %s", msg.channel)
            except asyncio.TimeoutError:
                continue
            except asyncio.CancelledError:
                break

    def get_channel(self, name: str) -> BaseChannel | None:
        """Get a channel by name."""
        return self.channels.get(name)

    def get_status(self) -> dict[str, Any]:
        """Get status of all channels."""
        return {
            name: {"enabled": True, "running": channel.is_running}
            for name, channel in self.channels.items()
        }

    @property
    def enabled_channels(self) -> list[str]:
        """Get list of registered channel names."""
        return list(self.channels.keys())
