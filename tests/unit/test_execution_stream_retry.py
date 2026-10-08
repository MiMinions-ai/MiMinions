"""Dispatch streaming retries cannot repeat visible output or tool execution."""

import pytest
from pydantic_ai.exceptions import ModelHTTPError
from pydantic_ai.models.test import TestModel

from miminions.agent import create_minion
from miminions.execution import ExecutionRequest
from miminions.execution.handlers import TaskContext, _stream
from miminions.execution.store import ExecutionStore


@pytest.mark.parametrize("activity", ["none", "text", "tool"])
async def test_retry_only_before_output_and_tool_activity(tmp_path, activity):
    store = ExecutionStore(tmp_path)
    task_id = store.enqueue(ExecutionRequest("prompt"))
    context = TaskContext(store, store.claim())
    agent = context.wire(create_minion("Test", model=TestModel(), retry_base_delay=0))
    attempts = []

    async def stream(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            if activity == "text":
                yield "partial"
            elif activity == "tool":
                agent._on_tool_call("operation", {})
            raise ModelHTTPError(status_code=500, model_name="test")
        yield "recovered"

    agent.run_stream = stream
    if activity == "none":
        assert await _stream(context, agent, "hello") == "recovered"
        assert len(attempts) == 2
        assert sum(e.type == "retry" for e in store.events(task_id)) == 1
    else:
        with pytest.raises(ModelHTTPError):
            await _stream(context, agent, "hello")
        assert len(attempts) == 1
        assert not any(e.type == "retry" for e in store.events(task_id))
