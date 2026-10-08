"""Conversation handler persistence and streaming across isolated turn lifecycles."""

import json
from unittest.mock import Mock

import pytest
from pydantic_ai.messages import ModelMessagesTypeAdapter
from pydantic_ai.models.test import TestModel

from miminions.agent import create_minion
from miminions.core.workspace import WorkspaceManager, ensure_workspace
from miminions.execution import ExecutionRequest
from miminions.execution.handlers import TaskContext, get_handler
from miminions.execution.store import ExecutionStore
from miminions.session.store import JsonlSessionStore


@pytest.fixture
def conversation(tmp_path, monkeypatch):
    home = tmp_path / "home"
    manager = WorkspaceManager(home)
    workspace = manager.create_workspace("Chat")
    workspace.root_path = str(tmp_path / "workspace")
    manager.save_workspaces({workspace.id: workspace})
    _, root = ensure_workspace(manager, workspace.id, init_files=True)
    store = ExecutionStore(home)
    agents = []

    def factory(**kwargs):
        agent = create_minion(**kwargs, model=TestModel(custom_output_text="reply", call_tools=[]))
        agents.append(agent)
        return agent

    monkeypatch.setattr("miminions.agent.create_minion", factory)
    return store, workspace, root, agents


def turn_context(conversation, prompt="hello", session="session"):
    store, workspace, _, _ = conversation
    key = f"workspace:{workspace.id}:session:{session}"
    task_id = store.enqueue(ExecutionRequest("chat_turn", {"workspace": workspace.id, "session_id": session, "prompt": prompt}, session_key=key))
    return TaskContext(store, store.claim())


async def test_turn_stream_and_transcript_include_task_ids(conversation):
    context = turn_context(conversation)
    result = await get_handler("chat_turn")(context)
    assert result == "reply"
    events = context.store.events(context.task.id)
    assert "".join(e.data["text"] for e in events if e.type == "text_delta") == "reply"
    records = list(JsonlSessionStore(conversation[2]).iter_messages("session"))
    assert [r["role"] for r in records] == ["user", "assistant"]
    assert all(r["meta"]["task_id"] == context.task.id for r in records)
    assert any(e.type == "turn_end" for e in events)


async def test_next_turn_restores_complete_model_checkpoint(conversation):
    first = turn_context(conversation)
    await get_handler("chat_turn")(first)
    first.store.finish(first.task.id, "completed")
    saved = ModelMessagesTypeAdapter.validate_json(first.store.checkpoint(first.task.request.session_key))
    assert len(saved) >= 2
    second = turn_context(conversation, "second")
    await get_handler("chat_turn")(second)
    assert len(conversation[3][-1]._last_messages) > len(saved)
    assert len(list(JsonlSessionStore(conversation[2]).iter_messages("session"))) == 4


async def test_checkpoint_preserves_tool_call_and_return_pairs(conversation, monkeypatch):
    def factory(**kwargs):
        agent = create_minion(**kwargs, model=TestModel(call_tools=["add"]))
        def add(a: int, b: int) -> int:
            return a + b
        agent.register_tool("add", "Add numbers", add)
        return agent

    monkeypatch.setattr("miminions.agent.create_minion", factory)
    context = turn_context(conversation)
    await get_handler("chat_turn")(context)
    history = ModelMessagesTypeAdapter.validate_json(context.store.checkpoint(context.task.request.session_key))
    parts = [part for message in history for part in message.parts]
    assert any(part.part_kind == "tool-call" for part in parts)
    assert any(part.part_kind == "tool-return" for part in parts)


async def test_one_shot_prompt_and_chat_share_session_checkpoint(conversation):
    first = turn_context(conversation)
    await get_handler("chat_turn")(first)
    first.store.finish(first.task.id, "completed")
    request = ExecutionRequest("prompt", {**first.params, "prompt": "one shot"}, session_key=first.task.request.session_key)
    first.store.enqueue(request)
    prompt = TaskContext(first.store, first.store.claim())
    await get_handler("prompt")(prompt)
    first.store.finish(prompt.task.id, "completed")
    last = turn_context(conversation, "back to chat")
    await get_handler("chat_turn")(last)
    records = list(JsonlSessionStore(conversation[2]).iter_messages("session"))
    assert len(records) == 6
    assert records[2]["meta"]["source"] == "cli-prompt"
    history = ModelMessagesTypeAdapter.validate_json(last.store.checkpoint(last.task.request.session_key))
    assert len(history) >= 6


async def test_resume_transcript_without_checkpoint(conversation):
    transcript = JsonlSessionStore(conversation[2])
    transcript.append("session", "user", "previous")
    transcript.append("session", "assistant", "answer")
    context = turn_context(conversation)
    await get_handler("chat_turn")(context)
    assert len(conversation[3][-1]._last_messages) >= 4


async def test_partial_failure_persists_output_and_does_not_replace_checkpoint(conversation, monkeypatch):
    first = turn_context(conversation)
    await get_handler("chat_turn")(first)
    first.store.finish(first.task.id, "completed")
    checkpoint = first.store.checkpoint(first.task.request.session_key)
    second = turn_context(conversation, "fail")
    factory = __import__("miminions.agent", fromlist=["create_minion"]).create_minion

    def failing_factory(**kwargs):
        agent = factory(**kwargs)
        async def stream(*args, **kwargs):
            yield "partial"
            raise RuntimeError("midstream")
        agent.run_stream = stream
        return agent

    monkeypatch.setattr("miminions.agent.create_minion", failing_factory)
    with pytest.raises(RuntimeError, match="midstream"):
        await get_handler("chat_turn")(second)
    records = list(JsonlSessionStore(conversation[2]).iter_messages("session"))
    assert records[-1]["content"] == "partial\n[error] RuntimeError: midstream"
    assert records[-1]["meta"]["error"] is True
    assert first.store.checkpoint(first.task.request.session_key) == checkpoint


async def test_distillation_is_visible_and_cleans_up(conversation, monkeypatch):
    store, workspace, _, agents = conversation
    distill = Mock()
    monkeypatch.setattr("miminions.cli.chat._run_session_distillation", distill)
    task_id = store.enqueue(ExecutionRequest("session_distill", {"workspace": workspace.id, "session_id": "session"}))
    context = TaskContext(store, store.claim())
    await get_handler("session_distill")(context)
    distill.assert_called_once()
    assert any(e.data.get("message") == "Distilling session memory..." for e in store.events(task_id))
    assert agents


async def test_distillation_failure_is_recorded_as_a_task_failure(conversation, monkeypatch):
    store, workspace, _, _ = conversation
    monkeypatch.setattr("miminions.cli.chat._run_session_distillation", Mock(side_effect=RuntimeError("distillation failed")))
    task_id = store.enqueue(ExecutionRequest("session_distill", {"workspace": workspace.id, "session_id": "session"}))
    from miminions.execution.worker import _run_task
    store.claim()
    await _run_task(store, task_id)
    assert any(e.type == "outcome" and "distillation failed" in e.data.get("error", "") for e in store.events(task_id))
