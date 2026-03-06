"""Startup orchestration for the gateway runtime.

Manages ordered phase execution with graceful shutdown in reverse order:
    Startup:  BUS → SERVICES → CHANNELS
    Shutdown: CHANNELS → SERVICES → BUS

Subclass ``GatewayOrchestrator`` and implement ``configure()`` to wire
your components into the appropriate phases.
"""

import asyncio
import logging
from abc import ABC, abstractmethod
from enum import IntEnum
from typing import Any

logger = logging.getLogger(__name__)


class Phase(IntEnum):
    """Startup phases, executed in ascending order.  Shutdown runs in reverse."""

    BUS = 1
    SERVICES = 2
    CHANNELS = 3


class Lifecycle(ABC):
    """Abstract interface for components that participate in startup/shutdown."""

    @abstractmethod
    async def start(self) -> None:
        """Start the component."""

    @abstractmethod
    async def stop(self) -> None:
        """Stop the component and release resources."""


class GatewayOrchestrator(ABC):
    """
    Abstract orchestrator for gateway startup and graceful shutdown.

    Concrete subclasses implement ``configure()`` to register components
    (MessageBus, CronService, ChannelManager, etc.) into their phases
    via ``self.register(phase, component)``.

    Example::

        class MyGateway(GatewayOrchestrator):
            async def configure(self) -> None:
                self.register(Phase.BUS,      BusLifecycle(self.bus))
                self.register(Phase.SERVICES,  CronLifecycle(self.cron))
                self.register(Phase.CHANNELS,  ChannelLifecycle(self.channels))
    """

    def __init__(self) -> None:
        self._phases: dict[Phase, list[Lifecycle]] = {phase: [] for phase in Phase}
        self._running = False

    @abstractmethod
    async def configure(self) -> None:
        """Register components into their respective phases.

        Called once at the beginning of ``start()``.
        """

    def register(self, phase: Phase, component: Lifecycle) -> None:
        """Register a lifecycle component into a startup phase."""
        self._phases[phase].append(component)

    async def start(self) -> None:
        """Configure and start all components in phase order."""
        await self.configure()

        for phase in sorted(Phase):
            for component in self._phases[phase]:
                name = type(component).__name__
                try:
                    await component.start()
                    logger.info("Started %s in phase %s", name, phase.name)
                except Exception:
                    logger.exception(
                        "Failed to start %s in phase %s — initiating shutdown",
                        name,
                        phase.name,
                    )
                    await self.shutdown()
                    raise

        self._running = True
        logger.info("Gateway started successfully")

    async def shutdown(self) -> None:
        """Stop all components in reverse phase order."""
        logger.info("Gateway shutting down...")

        for phase in sorted(Phase, reverse=True):
            for component in reversed(self._phases[phase]):
                name = type(component).__name__
                try:
                    await component.stop()
                    logger.info("Stopped %s in phase %s", name, phase.name)
                except Exception:
                    logger.exception("Error stopping %s in phase %s", name, phase.name)

        self._running = False
        logger.info("Gateway stopped")

    @property
    def is_running(self) -> bool:
        return self._running

    def get_status(self) -> dict[str, Any]:
        """Return a summary of registered components per phase."""
        return {
            phase.name: [type(c).__name__ for c in components]
            for phase, components in self._phases.items()
        }
