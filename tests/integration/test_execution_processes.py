"""Real isolated processes, without model network calls."""

import json
import os
import subprocess
import sys
import shlex
import re
import time
from concurrent.futures import ThreadPoolExecutor

import pytest

from miminions.execution import ExecutionRequest, ExecutionService
from miminions.execution.models import TERMINAL
from miminions.execution.processes import alive


def wait_for(predicate, timeout=30):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        result = predicate()
        if result:
            return result
        time.sleep(0.05)
    raise AssertionError("Timed out waiting for execution state")


@pytest.fixture
def service(tmp_path):
    execution = ExecutionService(tmp_path / "home")
    try:
        yield execution
    finally:
        execution.stop(cancel=True)
        wait_for(lambda: not execution.status().get("healthy"), timeout=20)


def tool_request(tmp_path, body, *, key=None, name="probe"):
    module = tmp_path / (name + ".py")
    module.write_text("from miminions.tools import create_tool\n" + body +
                      f"\nregistered = create_tool({name!r}, 'Process probe', probe)\n", encoding="utf-8")
    return ExecutionRequest("session_tool", {
        "session_id": name, "session": {"tool_sources": [{"type": "module", "path": str(module)}]},
        "tool_name": name, "inputs": {},
    }, str(tmp_path), key)


def test_detached_output_is_live_and_replayable(service, tmp_path):
    request = tool_request(tmp_path, "import time\ndef probe():\n    print('early', flush=True)\n    time.sleep(1.5)\n    print('late', flush=True)\n    return 'done'\n")
    handle = service.submit(request)
    wait_for(lambda: any("early" in e.data.get("text", "") for e in service.store.events(handle.id)))
    assert handle.get().status not in TERMINAL
    events = list(handle.follow())
    assert handle.get().status == "completed", handle.get().error
    output = "".join(e.data.get("text", "") for e in events if e.type == "stdout")
    assert "early" in output and "late" in output and "Result: done" in output
    assert events == list(handle.follow())
    after = events[2].sequence
    assert list(handle.follow(after)) == [e for e in events if e.sequence > after]
    workflow = json.loads((service.store.home / "interactions.json").read_text())
    assert "early" in workflow["probe"][0]["trace"][1]["kwargs"]["__stdout__"]


def test_concurrent_first_submissions_start_one_instance(service, tmp_path):
    request = tool_request(tmp_path, "def probe():\n    return 'ok'\n")
    with ThreadPoolExecutor(max_workers=4) as pool:
        handles = list(pool.map(lambda _: service.submit(request), range(4)))
    pid = service.status()["pid"]
    for handle in handles:
        list(handle.follow())
        assert handle.get().status == "completed", handle.get().error
    assert service.status()["pid"] == pid
    assert len({h.id for h in handles}) == 4


def test_blocking_task_heartbeat_cancellation_and_descendant_cleanup(service, tmp_path):
    pid_file = tmp_path / "descendant.pid"
    body = ("import subprocess, sys, time\nfrom pathlib import Path\ndef probe():\n"
            "    child = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(120)'])\n"
            f"    Path({str(pid_file)!r}).write_text(str(child.pid))\n"
            "    time.sleep(120)\n")
    handle = service.submit(tool_request(tmp_path, body, key="held-session"))
    queued = service.submit(tool_request(tmp_path, "def probe():\n    return 'next'\n", key="held-session", name="queued_probe"))
    wait_for(pid_file.exists)
    descendant = int(pid_file.read_text())
    assert alive(descendant)
    wait_for(lambda: any(e.type == "heartbeat" for e in service.store.events(handle.id)), timeout=12)
    wait_for(lambda: any(e.type == "heartbeat" and e.data.get("status") == "queued"
                        for e in service.store.events(queued.id)), timeout=12)
    assert queued.get().status == "queued"
    handle.cancel()
    list(handle.follow())
    assert handle.get().status == "cancelled"
    wait_for(lambda: not alive(descendant))
    list(queued.follow())
    assert queued.get().status == "completed", queued.get().error


def test_approval_waits_then_streams_command_output(service, tmp_path):
    # Directly execute the wired default tool; approval must survive a detached client.
    args = [sys.executable, "-u", "-c", "print('approved')"]
    command = subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)
    request = ExecutionRequest("agent_tool", {"agent": {"name": "A"}, "tool_name": "cli_run_command",
                                              "arguments": {"command": command}}, str(tmp_path))
    handle = service.submit(request)
    wait_for(lambda: handle.get().status == "waiting_for_input")
    approval = service.store.approvals(handle.id)[0]
    service.approve(handle.id, approval["id"], True)
    events = list(handle.follow())
    assert handle.get().status == "completed", handle.get().error
    assert any("approved" in e.data.get("text", "") for e in events)


def test_session_ordering_and_failures_keep_partial_output(service, tmp_path):
    first = service.submit(tool_request(tmp_path, "import time\ndef probe():\n    print('partial', flush=True)\n    time.sleep(.5)\n    raise ValueError('deliberate')\n", key="session", name="first"))
    second = service.submit(tool_request(tmp_path, "def probe():\n    return 'next'\n", key="session", name="second"))
    list(first.follow())
    list(second.follow())
    assert first.get().status == "failed"
    assert "deliberate" in first.get().error
    assert any("partial" in e.data.get("text", "") for e in service.store.events(first.id))
    assert second.get().status == "completed", second.get().error
    assert second.get().started_at >= first.get().ended_at


def test_supervisor_crash_fails_active_task_and_preserves_queue(service, tmp_path):
    service.store.home.joinpath("config.json").write_text(json.dumps({"execution": {"max_concurrency": 1}}))
    active = service.submit(tool_request(tmp_path, "import time\ndef probe():\n    print('active', flush=True)\n    time.sleep(120)\n", name="active"))
    queued = service.submit(tool_request(tmp_path, "def probe():\n    return 'survived'\n", name="queued"))
    wait_for(lambda: any("active" in e.data.get("text", "") for e in service.store.events(active.id)))
    old_pid = service.status()["pid"]
    if os.name == "nt":
        import ctypes
        from ctypes import wintypes
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.OpenProcess.restype = wintypes.HANDLE
        kernel.OpenProcess.argtypes = [wintypes.DWORD, wintypes.BOOL, wintypes.DWORD]
        kernel.TerminateProcess.argtypes = [wintypes.HANDLE, wintypes.UINT]
        kernel.CloseHandle.argtypes = [wintypes.HANDLE]
        handle = kernel.OpenProcess(1, False, old_pid)
        assert handle
        try:
            assert kernel.TerminateProcess(handle, 1)
        finally:
            kernel.CloseHandle(handle)
    else:
        import signal
        os.kill(old_pid, signal.SIGKILL)
    wait_for(lambda: not service.status().get("healthy"))
    service.ensure_instance()
    assert active.get().status == "failed"
    list(queued.follow())
    assert queued.get().status == "completed", queued.get().error


def test_warm_cli_detach_acknowledges_within_one_second(service, tmp_path):
    from miminions.core.bootstrap import ensure_default_setup
    from miminions.execution.service import worker_environment
    ensure_default_setup(service.store.home)
    service.ensure_instance()
    env = {**worker_environment(), "MIMINIONS_HOME": str(service.store.home)}
    started = time.monotonic()
    result = subprocess.run([sys.executable, "-m", "miminions", "tool", "execute", "cli_add",
                             "--arguments", '{"a":2,"b":3}', "--detach"], env=env,
                            capture_output=True, text=True, timeout=10)
    elapsed = time.monotonic() - started
    assert result.returncode == 0, result.stderr
    assert result.stdout == ""
    assert "accepted; follow with miminions task tail exec_" in result.stderr
    assert elapsed < 1, f"Warm CLI acknowledgement took {elapsed:.2f}s"
    task = service.store.list()[0]
    list(service.follow(task.id))
    assert service.get(task.id).status == "completed", service.get(task.id).error


def test_broken_cli_output_pipe_detaches_with_130_and_task_finishes(service, tmp_path):
    from miminions.core.bootstrap import ensure_default_setup
    from miminions.core.persistence import save_json
    from miminions.execution.service import worker_environment
    request = tool_request(tmp_path, "import time\ndef probe():\n    print('early', flush=True)\n    time.sleep(1)\n    print('late', flush=True)\n    return 'done'\n")
    ensure_default_setup(service.store.home)
    save_json(service.store.home / "sessions.json", {"probe": {**request.params["session"], "status": "active"}})
    env = {**worker_environment(), "MIMINIONS_HOME": str(service.store.home), "OPENROUTER_API_KEY": "test-placeholder"}
    process = subprocess.Popen([sys.executable, "-m", "miminions", "tool", "session", "execute", "probe"],
                               env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
    process.stdout.close()
    process.stdout = None
    _, stderr = process.communicate(timeout=30)
    assert process.returncode == 130, stderr
    assert "Exception ignored" not in stderr
    assert "Detached; task" in stderr
    task_id = re.search(r"Task (exec_[a-f0-9]+) accepted", stderr).group(1)
    assert not service.get(task_id).cancel_requested
    list(service.follow(task_id))
    assert service.get(task_id).status == "completed", service.get(task_id).error
    assert any("late" in e.data.get("text", "") for e in service.store.events(task_id))


def test_nested_command_helper_uses_task_approval_broker(service, tmp_path):
    args = [sys.executable, "-u", "-c", "print('nested')"]
    command = subprocess.list2cmdline(args) if os.name == "nt" else shlex.join(args)
    body = ("from miminions.tools.default import cli_run_command\n"
            f"def probe():\n    return cli_run_command({command!r})\n")
    handle = service.submit(tool_request(tmp_path, body))
    wait_for(lambda: handle.get().status == "waiting_for_input")
    request = service.store.approvals(handle.id)[0]
    service.approve(handle.id, request["id"], True)
    list(handle.follow())
    assert handle.get().status == "completed", handle.get().error
    assert handle.get().result["stdout"].strip() == "nested"


def test_configured_tool_can_override_builtin_without_schema_changes(service, tmp_path):
    request = tool_request(tmp_path, "def probe():\n    return 'custom override'\n", name="cli_run_command")
    handle = service.submit(request)
    list(handle.follow())
    assert handle.get().status == "completed", handle.get().error
    assert handle.get().result == "custom override"
