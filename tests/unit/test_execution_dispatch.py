"""Transactional execution and terminal rendering contracts."""

import json
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import Mock

import click
import pytest
from click.testing import CliRunner

from miminions.cli.dispatch import follow_task, submit_task
from miminions.execution import ExecutionRequest, ExecutionService
from miminions.execution.models import TaskHandle
from miminions.execution.store import ExecutionStore


def test_queue_claims_once_and_serializes_sessions(tmp_path):
    store = ExecutionStore(tmp_path)
    first = store.enqueue(ExecutionRequest("prompt", session_key="one"))
    second = store.enqueue(ExecutionRequest("prompt", session_key="one"))
    other = store.enqueue(ExecutionRequest("prompt", session_key="two"))
    with ThreadPoolExecutor(max_workers=8) as pool:
        claimed = list(pool.map(lambda _: store.claim(), range(8)))
    assert {t.id for t in claimed if t} == {first, other}
    store.finish(first, "completed", result="done")
    assert store.claim().id == second


def test_event_sequences_terminal_races_and_checkpoint(tmp_path):
    store = ExecutionStore(tmp_path)
    task_id = store.enqueue(ExecutionRequest("prompt"))
    store.claim()
    with ThreadPoolExecutor(max_workers=6) as pool:
        list(pool.map(lambda i: store.append(task_id, "text_delta", {"text": str(i)}), range(30)))
    store.cancel(task_id)
    assert store.finish(task_id, "completed", result="race")
    assert not store.finish(task_id, "failed", error="late")
    assert store.get(task_id).status == "cancelled"
    events = store.events(task_id)
    assert [e.sequence for e in events] == list(range(1, len(events) + 1))
    assert events[-1].type == "cancelled"
    store.append(task_id, "stdout", {"text": "late"})
    assert store.events(task_id) == events
    store.save_checkpoint("session", '[{"history":true}]')
    assert ExecutionStore(tmp_path).checkpoint("session") == '[{"history":true}]'


def test_approvals_are_scoped_single_answer_and_cancel_safe(tmp_path):
    store = ExecutionStore(tmp_path)
    task_id = store.enqueue(ExecutionRequest("agent_tool"))
    store.claim()
    request_id = store.request_approval(task_id, "Run command?")
    assert store.get(task_id).status == "waiting_for_input"
    assert store.approval_response(task_id, request_id) is None
    with pytest.raises(ValueError):
        store.approve("wrong_task", request_id, True)
    store.approve(task_id, request_id, False)
    assert store.approval_response(task_id, request_id) is False
    assert store.get(task_id).status == "running"
    with pytest.raises(ValueError):
        store.approve(task_id, request_id, True)
    pending = store.request_approval(task_id, "Another command?")
    store.cancel(task_id)
    with pytest.raises(ValueError):
        store.approve(task_id, pending, True)


def test_recovery_preserves_queue_and_does_not_replay_started_work(tmp_path):
    store = ExecutionStore(tmp_path)
    started = store.enqueue(ExecutionRequest("agent_tool"))
    queued = store.enqueue(ExecutionRequest("agent_tool"))
    store.claim()
    store.recover()
    assert store.get(started).status == "failed"
    assert "Inspect output" in store.get(started).error
    assert store.get(queued).status == "queued"
    assert store.claim().id == queued


def test_execution_remove_protects_active_tasks(tmp_path):
    store = ExecutionStore(tmp_path)
    task_id = store.enqueue(ExecutionRequest("agent_tool"))
    with pytest.raises(ValueError, match="Cancel"):
        store.remove(task_id)
    store.cancel(task_id)
    store.remove(task_id)
    assert store.events(task_id) == []
    with pytest.raises(ValueError):
        store.get(task_id)


def test_acknowledgement_precedes_release_and_detach_does_not_follow(tmp_path, monkeypatch):
    service = ExecutionService(tmp_path)
    monkeypatch.setattr(service, "ensure_instance", lambda on_start=None: None)
    monkeypatch.setattr("miminions.cli.dispatch.ExecutionService", lambda home: service)
    release = TaskHandle.release
    calls = []
    echo = click.echo

    def record_echo(message, **kwargs):
        calls.append("ack")
        assert "accepted; follow with miminions task tail exec_" in message
        echo(message, **kwargs)

    def record_release(handle):
        calls.append("release")
        assert service.store.claim() is None
        release(handle)

    monkeypatch.setattr("miminions.cli.dispatch.click.echo", record_echo)
    monkeypatch.setattr(TaskHandle, "release", record_release)
    handle = submit_task("agent_ask", {"prompt": "hello"}, detach=True, home=tmp_path)
    assert calls == ["ack", "release"]
    assert service.store.claim().id == handle.id


@pytest.mark.parametrize("status,code", [("completed", 0), ("failed", 1), ("cancelled", 130)])
def test_tail_stream_separation_json_replay_and_exit_codes(tmp_path, status, code):
    service = ExecutionService(tmp_path)
    task_id = service.store.enqueue(ExecutionRequest("prompt"))
    service.store.claim()
    service.store.append(task_id, "text_delta", {"text": "partial"})
    service.store.finish(task_id, status, error="bad" if status == "failed" else None)

    @click.command()
    def command():
        raise click.exceptions.Exit(follow_task(service, task_id))

    result = CliRunner().invoke(command)
    assert result.exit_code == code
    assert result.stdout == "partial"
    assert f"Task {task_id} {status}" in result.stderr

    @click.command()
    def json_command():
        raise click.exceptions.Exit(follow_task(service, task_id, after=2, as_json=True))

    result = CliRunner().invoke(json_command)
    events = [json.loads(line) for line in result.stdout.splitlines()]
    assert [e["sequence"] for e in events] == [3, 4]
    assert result.stderr == ""


@pytest.mark.parametrize("interruption", [KeyboardInterrupt, BrokenPipeError])
def test_interruption_only_detaches(tmp_path, monkeypatch, interruption):
    service = ExecutionService(tmp_path)
    task_id = service.store.enqueue(ExecutionRequest("prompt"))
    monkeypatch.setattr(service, "follow", Mock(side_effect=interruption))
    assert follow_task(service, task_id) == 130
    assert not service.get(task_id).cancel_requested


def test_source_and_frozen_launch_arguments(tmp_path, monkeypatch):
    from miminions.execution.service import worker_command
    assert "miminions.execution.worker" in worker_command(tmp_path)
    monkeypatch.setattr("sys.frozen", True, raising=False)
    assert worker_command(tmp_path, "exec_test")[1:] == ["_execution-worker", "--home", str(tmp_path), "--task", "exec_test"]


def test_serializable_contracts_round_trip(tmp_path):
    from miminions.execution.models import ExecutionTask, TaskEvent
    service = ExecutionService(tmp_path)
    request = ExecutionRequest("prompt", {"prompt": "hello"}, str(tmp_path), "session")
    task_id = service.store.enqueue(request)
    task = service.get(task_id)
    assert ExecutionRequest.from_dict(json.loads(json.dumps(request.to_dict()))) == request
    assert ExecutionTask.from_dict(json.loads(json.dumps(task.to_dict()))) == task
    event = service.store.events(task_id)[0]
    assert TaskEvent.from_dict(json.loads(json.dumps(event.to_dict()))) == event
    handle = TaskHandle(task_id, service)
    assert TaskHandle.from_dict(json.loads(json.dumps(handle.to_dict())), service).get() == task


def test_task_views_and_execution_record_protection(tmp_path, monkeypatch):
    from miminions.cli.task import task_cli, save_tasks
    monkeypatch.setattr("miminions.cli.task.get_config_dir", lambda: tmp_path)
    save_tasks({"todo": {"title": "Work", "description": "Description", "status": "pending"}})
    service = ExecutionService(tmp_path)
    task_id = service.store.enqueue(ExecutionRequest("agent_tool"))
    runner = CliRunner()
    result = runner.invoke(task_cli, ["list", "--json"])
    assert {t["kind"] for t in json.loads(result.stdout)} == {"execution", "work_item"}
    result = runner.invoke(task_cli, ["list", "--kind", "execution", "--json"])
    assert [t["id"] for t in json.loads(result.stdout)] == [task_id]
    result = runner.invoke(task_cli, ["show", task_id, "--json"])
    assert json.loads(result.stdout)["status"] == "queued"
    for args in (["update", task_id, "--status", "completed"], ["duplicate", task_id], ["remove", task_id, "--yes"]):
        assert runner.invoke(task_cli, args).exit_code == 1
    service.store.cancel(task_id)
    assert runner.invoke(task_cli, ["remove", task_id, "--yes"]).exit_code == 0


@pytest.mark.parametrize("args,kind", [
    (["prompt", "ask", "hello"], "prompt"),
    (["agent", "ask", "--prompt", "hello"], "agent_ask"),
    (["agent", "run"], "agent_run"),
    (["tool", "execute", "cli_add", "--arguments", '{"a":1,"b":2}'], "agent_tool"),
    (["tool", "session", "execute", "probe"], "session_tool"),
    (["tool", "test"], "tool_test"),
])
def test_every_execution_entry_point_uses_shared_dispatch(tmp_path, monkeypatch, args, kind):
    from miminions.cli.main import cli
    from miminions.core.bootstrap import ensure_default_setup
    from miminions.core.persistence import load_json, save_json
    monkeypatch.setenv("MIMINIONS_HOME", str(tmp_path))
    ensure_default_setup(tmp_path)
    agents = load_json(tmp_path / "agents.json")
    agents["default"]["goal"] = "A goal"
    save_json(tmp_path / "agents.json", agents)
    save_json(tmp_path / "sessions.json", {"session": {"status": "active", "tool_sources": []}})
    service = ExecutionService(tmp_path)
    monkeypatch.setattr(service, "ensure_instance", lambda on_start=None: None)
    monkeypatch.setattr("miminions.cli.dispatch.ExecutionService", lambda home: service)
    result = CliRunner().invoke(cli, [*args, "--detach"])
    assert result.exit_code == 0, result.output
    assert result.stdout == ""
    assert "accepted; follow with miminions task tail exec_" in result.stderr
    assert service.store.list()[0].request.kind == kind
    assert service.store.list()[0].status == "queued"
    conflict = CliRunner().invoke(cli, [*args, "--attach", "--detach"])
    assert conflict.exit_code == 2
    assert len(service.store.list()) == 1


def test_noninteractive_approval_guidance_never_answers(tmp_path, monkeypatch):
    service = ExecutionService(tmp_path)
    task_id = service.store.enqueue(ExecutionRequest("agent_tool"))
    service.store.claim()
    request_id = service.store.request_approval(task_id, "Execute sensitive command?")
    monkeypatch.setattr(service, "follow", lambda *args: iter(service.store.events(task_id)))
    monkeypatch.setattr("miminions.cli.dispatch.click.confirm", Mock(side_effect=AssertionError("Must not prompt")))

    @click.command()
    def command():
        # Finish after displaying the waiting state to avoid an intentionally infinite follow.
        def events(*args):
            yield from service.store.events(task_id)
            service.store.finish(task_id, "failed", error="test end")
        monkeypatch.setattr(service, "follow", events)
        follow_task(service, task_id)

    result = CliRunner().invoke(command)
    assert result.exit_code == 0, result.output
    assert f"task approve {task_id} {request_id} --allow or --deny" in result.stderr
    assert service.store.approval_response(task_id, request_id) is None


def test_startup_retries_when_previous_instance_is_releasing_lock(tmp_path, monkeypatch):
    import os
    from miminions.execution.store import now
    service = ExecutionService(tmp_path)
    attempts = []

    def launch(*args, **kwargs):
        attempts.append(1)
        if len(attempts) == 1:
            return Mock(poll=lambda: 0, returncode=0)
        service.store.set_instance(running=True, stopping=False, pid=os.getpid(), heartbeat=now())
        return Mock(poll=lambda: None)

    monkeypatch.setattr("miminions.execution.service.subprocess.Popen", launch)
    service.ensure_instance()
    assert len(attempts) == 2


def test_package_import_defers_model_stack_and_preserves_tool_shortcuts():
    import subprocess
    import sys
    from miminions.execution.service import worker_environment
    result = subprocess.run([sys.executable, "-c",
        "import miminions, sys; assert 'pydantic_ai' not in sys.modules; "
        "assert 'miminions.agent' not in sys.modules; "
        "from miminions import GenericTool, tool, create_tool; assert callable(create_tool)"],
        env=worker_environment(), capture_output=True, text=True, timeout=10)
    assert result.returncode == 0, result.stderr


def test_draining_rejects_submission_but_allows_following_and_cancellation(tmp_path):
    import os
    from miminions.execution.store import now
    service = ExecutionService(tmp_path)
    task_id = service.store.enqueue(ExecutionRequest("agent_tool"))
    service.store.claim()
    service.store.set_instance(running=True, stopping=True, pid=os.getpid(), heartbeat=now())
    with pytest.raises(ValueError, match="draining"):
        service.submit(ExecutionRequest("agent_tool"))
    events = service.follow(task_id)
    assert next(events).type == "accepted"
    service.cancel(task_id)
    assert service.get(task_id).cancel_requested
    service.store.finish(task_id, "cancelled")
    assert list(events)[-1].type == "cancelled"


def test_new_workspace_name_and_id_share_queue_identity_before_context_setup(tmp_path, monkeypatch):
    from miminions.cli.prompt import prompt_cli
    from miminions.core.workspace import WorkspaceManager
    service = ExecutionService(tmp_path)
    monkeypatch.setattr(service, "ensure_instance", lambda on_start=None: None)
    monkeypatch.setattr("miminions.cli.dispatch.ExecutionService", lambda home: service)
    monkeypatch.setattr("miminions.cli.prompt.get_config_dir", lambda: tmp_path)
    runner = CliRunner()
    first = runner.invoke(prompt_cli, ["ask", "hello", "--workspace", "New Workspace", "--session", "shared", "--detach"])
    assert first.exit_code == 0, first.output
    workspace = next(iter(WorkspaceManager(tmp_path).load_workspaces().values()))
    assert workspace.root_path is None  # Context/files are still deferred to execution.
    second = runner.invoke(prompt_cli, ["ask", "second", "--workspace", workspace.id, "--session", "shared", "--detach"])
    assert second.exit_code == 0, second.output
    tasks = service.store.list()
    assert tasks[0].request.session_key == tasks[1].request.session_key
    assert service.store.claim().id == tasks[0].id
    assert service.store.claim() is None


def test_sdk_submission_captures_callers_current_directory(tmp_path, monkeypatch):
    service = ExecutionService(tmp_path / "home")
    monkeypatch.setattr(service, "ensure_instance", lambda on_start=None: None)
    work = tmp_path / "work"
    work.mkdir()
    monkeypatch.chdir(work)
    handle = service.submit(ExecutionRequest("agent_tool"))
    assert handle.get().request.cwd == str(work.resolve())


def test_shutdown_race_cannot_accept_unowned_work(tmp_path):
    store = ExecutionStore(tmp_path)
    store.set_instance(running=False, stopping=False)
    with pytest.raises(ValueError, match="stopped during submission"):
        store.enqueue(ExecutionRequest("agent_tool"))
    assert store.list() == []


def test_conversation_key_matches_transcript_aliases():
    import os
    from miminions.execution.models import conversation_key
    assert conversation_key("workspace", " session ") == conversation_key("workspace", "session")
    if os.name == "nt":
        assert conversation_key("workspace", "SESSION") == conversation_key("workspace", "session")
