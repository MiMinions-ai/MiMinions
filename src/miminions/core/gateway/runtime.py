"""Concrete local gateway runtime assembly."""

from __future__ import annotations

from .channel import ChannelManager
from .orchestrator import GatewayOrchestrator, Lifecycle, Phase
from .services import CronService


class CronLifecycle(Lifecycle):
    """Lifecycle adapter for CronService."""

    def __init__(self, cron_service: CronService) -> None:
        self.cron_service = cron_service

    async def start(self) -> None:
        await self.cron_service.start()

    async def stop(self) -> None:
        await self.cron_service.stop()


class ChannelManagerLifecycle(Lifecycle):
    """Lifecycle adapter for ChannelManager."""

    def __init__(self, channel_manager: ChannelManager) -> None:
        self.channel_manager = channel_manager

    async def start(self) -> None:
        await self.channel_manager.start_all()

    async def stop(self) -> None:
        await self.channel_manager.stop_all()


class LocalGatewayRuntime(GatewayOrchestrator):
    """Local gateway runtime for the CLI entrypoint."""

    def __init__(
        self,
        channel_manager: ChannelManager,
        cron_service: CronService | None = None,
    ) -> None:
        super().__init__()
        self.channel_manager = channel_manager
        self.cron_service = cron_service

    async def configure(self) -> None:
        if self.cron_service is not None:
            self.register(Phase.SERVICES, CronLifecycle(self.cron_service))
        self.register(Phase.CHANNELS, ChannelManagerLifecycle(self.channel_manager))
