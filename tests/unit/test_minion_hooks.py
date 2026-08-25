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

    assert calls, f"expect calls to be non-empty, got {calls}"
    name, args = calls[0]
    assert name == "echo", f"expect the first tool call has name 'echo', got {name}"
    assert "text" in args, f"expect the first tool call arguments to contain 'text', got {args}"


async def test_on_turn_end_receives_usage_and_latency():
    turns = []
    minion = _make_minion(on_turn_end=lambda usage, latency: turns.append((usage, latency)))

    await minion.run("hello")

    no_turns = len(turns)
    assert no_turns == 1, f"expect the number of turns to be 1, got {no_turns}"
    usage, latency = turns[0]
    assert usage.requests >= 1, f"expect usage.requests >= 1, got {usage.requests}"
    assert latency >= 0, f"expect latency >= 0, got {latency}"


async def test_raising_callbacks_do_not_break_the_turn():
    def _boom(*_args):
        raise RuntimeError("callback exploded")

    minion = _make_minion(on_tool_call=_boom, on_turn_end=_boom)

    reply = await minion.run("hello")

    assert isinstance(reply, str), f"expect the minion.run() result to be a string, got {type(reply)}"


def test_handler_is_none_without_callback():
    minion = _make_minion()
    result = minion._make_event_stream_handler()

    assert result is None, f"expect the event stream handler to be None, got {result}"
