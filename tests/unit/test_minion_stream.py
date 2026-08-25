"""Unit tests for Minion.run_stream()."""

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.test import TestModel

from miminions.agent import create_minion


async def test_stream_yields_deltas_and_updates_history():
    minion = create_minion(
        name="Stream",
        model=TestModel(custom_output_text="hello world", call_tools=[]),
    )

    deltas = [delta async for delta in minion.run_stream("hi")]

    assert "".join(deltas) == "hello world", f"expect the joint string to be 'hello world', got {''.join(deltas)}"
    assert minion._last_messages, f"expect the minion._last_messages is not empty, got {minion._last_messages}"


async def test_stream_fires_on_turn_end():
    turns = []
    minion = create_minion(
        name="Stream",
        model=TestModel(call_tools=[]),
        on_turn_end=lambda usage, latency: turns.append((usage, latency)),
    )

    async for _ in minion.run_stream("hi"):
        pass

    assert len(turns) == 1, f"expect the length of turns to be 1, got {len(turns)}"
    usage, latency = turns[0]
    assert usage.requests >= 1, f"expect the usage.requests to be >= 1, got {usage.requests}"
    assert latency >= 0, f"expect the latency to be >= 0, got {latency}"


async def test_stream_error_propagates_and_history_unchanged(monkeypatch):
    minion = create_minion(name="Stream", model=TestModel())

    class _BoomAgent:
        def run_stream(self, *args, **kwargs):
            raise ModelHTTPError(status_code=500, model_name="test-model")

    monkeypatch.setattr(minion, "_rebuild_pydantic_ai_agent", lambda: None)
    minion._pydantic_ai_agent = _BoomAgent()
    minion._last_messages = ["sentinel"]

    with pytest.raises(ModelHTTPError):
        async for _ in minion.run_stream("hi"):
            pass

    assert minion._last_messages == ["sentinel"], f"expect the minion._last_messages to be ['sentinel'], got {minion._last_messages}"
