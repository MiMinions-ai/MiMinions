"""Unit tests for gateway.orchestrator module."""
import pytest

from miminions.core.gateway.orchestrator import (
    GatewayOrchestrator,
    Lifecycle,
    Phase,
)


# ── Phase enum tests ─────────────────────────────────────────────────


class TestPhase:
    def test_values(self):
        assert Phase.BUS == 1, f"expect Phase.BUS enum value for startup ordering is 1, got {Phase.BUS}"
        assert Phase.SERVICES == 2, f"expect Phase.SERVICES enum value for startup ordering is 2, got {Phase.SERVICES}"
        assert Phase.CHANNELS == 3, f"expect Phase.CHANNELS enum value for startup ordering is 3, got {Phase.CHANNELS}"

    def test_ordering(self):
        phases = sorted(Phase)
        assert phases == [Phase.BUS, Phase.SERVICES, Phase.CHANNELS], f"expect phase sort order is [BUS, SERVICES, CHANNELS] as {[Phase.BUS, Phase.SERVICES, Phase.CHANNELS]}, got {phases}"

    def test_reverse_ordering(self):
        phases = sorted(Phase, reverse=True)
        assert phases == [Phase.CHANNELS, Phase.SERVICES, Phase.BUS], f"expect reverse phase sort order is [CHANNELS, SERVICES, BUS] as {[Phase.CHANNELS, Phase.SERVICES, Phase.BUS]}, got {phases}"


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
        obj_is_lifecycle = isinstance(obj, Lifecycle)
        obj_type = type(obj)
        assert obj_is_lifecycle, f"expect concrete lifecycle object to implement Lifecycle as True, got {obj_type}"


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
        assert orch.is_running is False, f"expect newly created orchestrator running flag starts as {False}, got {orch.is_running}"
        status = orch.get_status()
        assert status == {"BUS": [], "SERVICES": [], "CHANNELS": []}, f"expect newly created orchestrator status mapping is {{'BUS': [], 'SERVICES': [], 'CHANNELS': []}}, got {status}"


class TestGatewayOrchestratorRegister:
    def test_register_components(self):
        orch = SimpleOrchestrator()
        log = []
        bus = FakeComponent("bus", log)
        svc = FakeComponent("svc", log)
        orch.register(Phase.BUS, bus)
        orch.register(Phase.SERVICES, svc)

        status = orch.get_status()
        assert status["BUS"] == ["FakeComponent"], f"expect get_status BUS phase includes one registered FakeComponent as ['FakeComponent'], got {status['BUS']}"
        assert status["SERVICES"] == ["FakeComponent"], f"expect get_status SERVICES phase includes one registered FakeComponent as ['FakeComponent'], got {status['SERVICES']}"
        assert status["CHANNELS"] == [], f"expect get_status CHANNELS phase remains empty as [], got {status['CHANNELS']}"

    def test_register_multiple_same_phase(self):
        orch = SimpleOrchestrator()
        log = []
        orch.register(Phase.BUS, FakeComponent("a", log))
        orch.register(Phase.BUS, FakeComponent("b", log))

        bus_component_count = len(orch._phases[Phase.BUS])
        assert bus_component_count == 2, f"expect register allows two components in BUS phase list as 2, got {bus_component_count}"


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
        assert orch.is_running is True, f"expect orchestrator running flag becomes {True} after successful start, got {orch.is_running}"
        assert log == ["start:bus", "start:svc", "start:chan"], f"expect components start in phase order as ['start:bus', 'start:svc', 'start:chan'], got {log}"

    async def test_configure_called(self):
        """configure() is called at the start of start()."""
        called = []

        class TrackingOrchestrator(GatewayOrchestrator):
            async def configure(self):
                called.append(True)

        orch = TrackingOrchestrator()
        await orch.start()
        assert called == [True], f"expect orchestrator start invokes configure hook once as [True], got {called}"

    async def test_start_with_no_components(self):
        orch = SimpleOrchestrator()
        await orch.start()
        assert orch.is_running is True, f"expect orchestrator running flag becomes {True} even with no registered components, got {orch.is_running}"


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
        assert orch.is_running is False, f"expect orchestrator running flag becomes {False} after shutdown, got {orch.is_running}"
        assert log == ["stop:chan", "stop:svc", "stop:bus"], f"expect components stop in reverse phase order as ['stop:chan', 'stop:svc', 'stop:bus'], got {log}"

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
        assert log == ["stop:bus2", "stop:bus1"], f"expect components in same phase stop in reverse registration order as ['stop:bus2', 'stop:bus1'], got {log}"

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
        assert orch.is_running is False, f"expect orchestrator running flag becomes {False} even when stop handlers raise errors, got {orch.is_running}"
        # Both components attempted to stop
        assert "stop:error-comp" in log, f"expect contains 'stop:error-comp', got {log}"
        assert "stop:bus" in log, f"expect contains 'stop:bus', got {log}"


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

        assert orch.is_running is False, f"expect orchestrator running flag remains {False} after component startup failure, got {orch.is_running}"
        # Bus started, svc started (then failed), chan never started
        assert "start:bus" in log, f"expect contains 'start:bus', got {log}"
        assert "start:svc" in log, f"expect contains 'start:svc', got {log}"
        assert "start:chan" not in log, f"expect not contains 'start:chan', got {log}"
        # Shutdown was triggered — bus should have been stopped
        assert "stop:bus" in log, f"expect contains 'stop:bus', got {log}"

    async def test_failure_in_first_phase(self):
        log = []
        orch = SimpleOrchestrator(
            {
                Phase.BUS: [FailingComponent("bus", log)],
            }
        )

        with pytest.raises(RuntimeError, match="bus failed"):
            await orch.start()

        assert orch.is_running is False, f"expect orchestrator running flag remains {False} when first startup phase fails, got {orch.is_running}"


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
        assert status["BUS"] == ["FakeComponent", "FakeComponent"], f"expect get_status BUS phase reflects two registered FakeComponent entries as ['FakeComponent', 'FakeComponent'], got {status['BUS']}"
        assert status["SERVICES"] == [], f"expect get_status SERVICES phase remains empty as [], got {status['SERVICES']}"
        assert status["CHANNELS"] == ["FakeComponent"], f"expect get_status CHANNELS phase reflects one registered FakeComponent entry as ['FakeComponent'], got {status['CHANNELS']}"
        await orch.shutdown()
