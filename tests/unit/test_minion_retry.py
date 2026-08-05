"""Unit tests for retry/timeout handling around Minion model calls."""

import pytest
from pydantic_ai.exceptions import ModelAPIError, ModelHTTPError
from pydantic_ai.models.test import TestModel

from miminions.agent.agent import Minion, _is_retryable_error


def _http_error(status_code: int) -> ModelHTTPError:
    return ModelHTTPError(status_code=status_code, model_name="test-model")


class _FakeResult:
    output = "ok"
    usage = None

    def all_messages(self):
        return ["message"]


class _FlakyAgent:
    """Stub pydantic_ai Agent whose run() fails N times before succeeding."""

    def __init__(self, failures):
        self._failures = list(failures)
        self.calls = 0

    async def run(self, *args, **kwargs):
        self.calls += 1
        if self._failures:
            raise self._failures.pop(0)
        return _FakeResult()


def _make_minion(**kwargs) -> Minion:
    return Minion(name="Retry", model=TestModel(), retry_base_delay=0, **kwargs)


def _stub_agent(minion: Minion, fake: _FlakyAgent, monkeypatch) -> None:
    monkeypatch.setattr(minion, "_rebuild_pydantic_ai_agent", lambda: None)
    minion._pydantic_ai_agent = fake


async def test_transient_errors_are_retried_then_succeed(monkeypatch):
    minion = _make_minion()
    fake = _FlakyAgent([_http_error(429), _http_error(500)])
    _stub_agent(minion, fake, monkeypatch)

    reply = await minion.run("hello")

    assert reply == "ok"
    assert fake.calls == 3
    assert minion._last_messages == ["message"]


async def test_non_retryable_error_raises_immediately(monkeypatch):
    minion = _make_minion()
    fake = _FlakyAgent([_http_error(401)])
    _stub_agent(minion, fake, monkeypatch)

    with pytest.raises(ModelHTTPError):
        await minion.run("hello")

    assert fake.calls == 1


async def test_exhausted_retries_reraise(monkeypatch):
    minion = _make_minion(max_retries=1)
    fake = _FlakyAgent([_http_error(503), _http_error(503)])
    _stub_agent(minion, fake, monkeypatch)

    with pytest.raises(ModelHTTPError):
        await minion.run("hello")

    assert fake.calls == 2


async def test_connection_errors_are_retried(monkeypatch):
    minion = _make_minion()
    fake = _FlakyAgent([ModelAPIError("test-model", "connection reset")])
    _stub_agent(minion, fake, monkeypatch)

    reply = await minion.run("hello")

    assert reply == "ok"
    assert fake.calls == 2


async def test_backoff_delays_double_per_attempt(monkeypatch):
    minion = Minion(name="Backoff", model=TestModel(), retry_base_delay=0.5)
    fake = _FlakyAgent([_http_error(429), _http_error(500)])
    _stub_agent(minion, fake, monkeypatch)

    delays = []

    async def _record_sleep(delay):
        delays.append(delay)

    monkeypatch.setattr("miminions.agent.agent.asyncio.sleep", _record_sleep)

    reply = await minion.run("hello")

    assert reply == "ok"
    assert delays == [0.5, 1.0]


@pytest.mark.parametrize(
    ("exc", "expected"),
    [
        (_http_error(429), True),
        (_http_error(500), True),
        (_http_error(503), True),
        (_http_error(400), False),
        (_http_error(401), False),
        (ModelAPIError("test-model", "boom"), True),
        (ValueError("boom"), False),
    ],
)
def test_is_retryable_error(exc, expected):
    assert _is_retryable_error(exc) is expected


def test_rebuild_passes_request_timeout(monkeypatch):
    captured = {}

    class _CapturingAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("miminions.agent.agent.Agent", _CapturingAgent)
    minion = Minion(name="Timeout", model=TestModel(), request_timeout=12.5)

    minion._rebuild_pydantic_ai_agent()

    assert captured["model_settings"] == {"timeout": 12.5}


def test_rebuild_omits_model_settings_without_timeout(monkeypatch):
    captured = {}

    class _CapturingAgent:
        def __init__(self, **kwargs):
            captured.update(kwargs)

    monkeypatch.setattr("miminions.agent.agent.Agent", _CapturingAgent)
    minion = Minion(name="NoTimeout", model=TestModel(), request_timeout=None)

    minion._rebuild_pydantic_ai_agent()

    assert captured["model_settings"] is None
