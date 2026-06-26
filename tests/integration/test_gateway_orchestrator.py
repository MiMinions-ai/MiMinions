"""Unit tests for gateway.orchestrator module."""
import pytest
import asyncio
from unittest.mock import AsyncMock

from miminions.core.gateway.orchestrator import (
    GatewayOrchestrator,
    Lifecycle,
    Phase,
)


# ── Phase enum tests ─────────────────────────────────────────────────


class TestPhase:
    def test_values(self):
        assert Phase.BUS == 1
        assert Phase.SERVICES == 2
        assert Phase.CHANNELS == 3

    def test_ordering(self):
        phases = sorted(Phase)
        assert phases == [Phase.BUS, Phase.SERVICES, Phase.CHANNELS]

    def test_reverse_ordering(self):
        phases = sorted(Phase, reverse=True)
        assert phases == [Phase.CHANNELS, Phase.SERVICES, Phase.BUS]


# ── Lifecycle ABC tests ──────────────────────────────────────────────


class TestLifecycle:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            Lifecycle()  # type: ignore

    def test_concrete_implementation(self):
        class ConcreteLifecycle(Lifecycle):
            async def start(self):
                pass

            async def stop(self):
                pass

        obj = ConcreteLifecycle()
        assert isinstance(obj, Lifecycle)


# ── Helpers ───────────────────────────────────────────────────────────


class FakeComponent(Lifecycle):
    """Tracks start/stop call order."""

    def __init__(self, name: str, log: list):
        self.name = name
        self._log = log

    async def start(self):
        self._log.append(f"start:{self.name}")

    async def stop(self):
        self._log.append(f"stop:{self.name}")


class FailingComponent(Lifecycle):
    """Fails on start."""

    def __init__(self, name: str, log: list):
        self.name = name
        self._log = log

    async def start(self):
        self._log.append(f"start:{self.name}")
        raise RuntimeError(f"{self.name} failed")

    async def stop(self):
        self._log.append(f"stop:{self.name}")


class SimpleOrchestrator(GatewayOrchestrator):
    """Minimal concrete orchestrator for testing."""

    def __init__(self, components: dict[Phase, list[Lifecycle]] | None = None):
        super().__init__()
        self._to_register = components or {}

    async def configure(self):
        for phase, comps in self._to_register.items():
            for c in comps:
                self.register(phase, c)


# ── GatewayOrchestrator tests ────────────────────────────────────────


class TestGatewayOrchestratorInit:
    def test_initial_state(self):
        orch = SimpleOrchestrator()
        assert orch.is_running is False
        assert orch.get_status() == {"BUS": [], "SERVICES": [], "CHANNELS": []}


class TestGatewayOrchestratorRegister:
    def test_register_components(self):
        orch = SimpleOrchestrator()
        log = []
        bus = FakeComponent("bus", log)
        svc = FakeComponent("svc", log)
        orch.register(Phase.BUS, bus)
        orch.register(Phase.SERVICES, svc)

        status = orch.get_status()
        assert status["BUS"] == ["FakeComponent"]
        assert status["SERVICES"] == ["FakeComponent"]
        assert status["CHANNELS"] == []

    def test_register_multiple_same_phase(self):
        orch = SimpleOrchestrator()
        log = []
        orch.register(Phase.BUS, FakeComponent("a", log))
        orch.register(Phase.BUS, FakeComponent("b", log))

        assert len(orch._phases[Phase.BUS]) == 2


class TestGatewayOrchestratorStart:
    async def test_start_order(self):
        """Components start in phase order: BUS → SERVICES → CHANNELS."""
        log = []
        orch = SimpleOrchestrator(
            {
                Phase.BUS: [FakeComponent("bus", log)],
                Phase.SERVICES: [FakeComponent("svc", log)],
                Phase.CHANNELS: [FakeComponent("chan", log)],
            }
        )

        await orch.start()
        assert orch.is_running is True
        assert log == ["start:bus", "start:svc", "start:chan"]

    async def test_configure_called(self):
        """configure() is called at the start of start()."""
        called = []

        class TrackingOrchestrator(GatewayOrchestrator):
            async def configure(self):
                called.append(True)

        orch = TrackingOrchestrator()
        await orch.start()
        assert called == [True]

    async def test_start_with_no_components(self):
        orch = SimpleOrchestrator()
        await orch.start()
        assert orch.is_running is True


class TestGatewayOrchestratorShutdown:
    async def test_shutdown_order(self):
        """Components stop in reverse phase order: CHANNELS → SERVICES → BUS."""
        log = []
        orch = SimpleOrchestrator(
            {
                Phase.BUS: [FakeComponent("bus", log)],
                Phase.SERVICES: [FakeComponent("svc", log)],
                Phase.CHANNELS: [FakeComponent("chan", log)],
            }
        )

        await orch.start()
        log.clear()

        await orch.shutdown()
        assert orch.is_running is False
        assert log == ["stop:chan", "stop:svc", "stop:bus"]

    async def test_shutdown_reverse_within_phase(self):
        """Multiple components in a phase stop in reverse registration order."""
        log = []
        orch = SimpleOrchestrator(
            {
                Phase.BUS: [FakeComponent("bus1", log), FakeComponent("bus2", log)],
            }
        )

        await orch.start()
        log.clear()

        await orch.shutdown()
        assert log == ["stop:bus2", "stop:bus1"]

    async def test_shutdown_continues_on_error(self):
        """Stop errors in one component shouldn't prevent stopping others."""
        log = []

        class ErrorOnStop(Lifecycle):
            async def start(self):
                log.append("start:error-comp")

            async def stop(self):
                log.append("stop:error-comp")
                raise RuntimeError("stop error")

        orch = SimpleOrchestrator(
            {
                Phase.CHANNELS: [ErrorOnStop()],
                Phase.BUS: [FakeComponent("bus", log)],
            }
        )

        await orch.start()
        log.clear()

        await orch.shutdown()
        assert orch.is_running is False
        # Both components attempted to stop
        assert "stop:error-comp" in log
        assert "stop:bus" in log


class TestGatewayOrchestratorStartFailure:
    async def test_start_failure_triggers_shutdown(self):
        """If a component fails to start, shutdown is called and error re-raised."""
        log = []
        orch = SimpleOrchestrator(
            {
                Phase.BUS: [FakeComponent("bus", log)],
                Phase.SERVICES: [FailingComponent("svc", log)],
                Phase.CHANNELS: [FakeComponent("chan", log)],
            }
        )

        with pytest.raises(RuntimeError, match="svc failed"):
            await orch.start()

        assert orch.is_running is False
        # Bus started, svc started (then failed), chan never started
        assert "start:bus" in log
        assert "start:svc" in log
        assert "start:chan" not in log
        # Shutdown was triggered — bus should have been stopped
        assert "stop:bus" in log

    async def test_failure_in_first_phase(self):
        log = []
        orch = SimpleOrchestrator(
            {
                Phase.BUS: [FailingComponent("bus", log)],
            }
        )

        with pytest.raises(RuntimeError, match="bus failed"):
            await orch.start()

        assert orch.is_running is False


class TestGatewayOrchestratorAbstract:
    def test_cannot_instantiate(self):
        with pytest.raises(TypeError):
            GatewayOrchestrator()  # type: ignore


class TestGatewayOrchestratorGetStatus:
    async def test_status_reflects_registered_components(self):
        log = []
        orch = SimpleOrchestrator(
            {
                Phase.BUS: [FakeComponent("b1", log), FakeComponent("b2", log)],
                Phase.CHANNELS: [FakeComponent("c1", log)],
            }
        )
        await orch.start()

        status = orch.get_status()
        assert status["BUS"] == ["FakeComponent", "FakeComponent"]
        assert status["SERVICES"] == []
        assert status["CHANNELS"] == ["FakeComponent"]
        await orch.shutdown()
