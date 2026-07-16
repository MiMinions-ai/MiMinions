"""Unit tests for Minion observability hooks (on_tool_call / on_turn_end)."""

from pydantic_ai.models.test import TestModel

from miminions.agent import create_minion


def _echo(text: str) -> str:
    """Echo tool used to trigger a controlled tool call."""
    return text


def _make_minion(**kwargs):
    # call_tools must stay restricted to the harmless echo tool: TestModel
    # invokes every listed tool, and Minion always registers cli_run_command,
    # which executes a real shell command.
    minion = create_minion(name="Hooks", model=TestModel(call_tools=["echo"]), **kwargs)
    minion.register_tool("echo", "Echo text back", _echo)
    return minion


async def test_on_tool_call_fires_with_name_and_args():
    calls = []
    minion = _make_minion(on_tool_call=lambda name, args: calls.append((name, args)))

    await minion.run("use the echo tool")

    assert calls, "expected at least one tool-call event"
    name, args = calls[0]
    assert name == "echo"
    assert "text" in args


async def test_on_turn_end_receives_usage_and_latency():
    turns = []
    minion = _make_minion(on_turn_end=lambda usage, latency: turns.append((usage, latency)))

    await minion.run("hello")

    assert len(turns) == 1
    usage, latency = turns[0]
    assert usage.requests >= 1
    assert latency >= 0


async def test_raising_callbacks_do_not_break_the_turn():
    def _boom(*_args):
        raise RuntimeError("callback exploded")

    minion = _make_minion(on_tool_call=_boom, on_turn_end=_boom)

    reply = await minion.run("hello")

    assert isinstance(reply, str)


def test_handler_is_none_without_callback():
    minion = _make_minion()

    assert minion._make_event_stream_handler() is None
