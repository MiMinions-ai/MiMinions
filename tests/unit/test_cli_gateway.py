import asyncio
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import click
import pytest

from miminions.cli.gateway import (
    GatewayPaths,
    _build_cron_service,
    _confirm_or_force,
    _default_cron_handler,
    _echo_job_list,
    _format_ms_timestamp,
    _format_schedule,
    _get_gateway_paths,
    _get_workspace_or_raise,
    _message_preview,
    _parse_iso_datetime_to_ms,
    _resolve_workspace,
    _validate_name_and_message,
    gateway_cli,
)
from miminions.core.gateway import CronJob, CronJobState, CronPayload, CronSchedule, SessionManager


class DummyManager:
    def __init__(self, workspaces):
        self._workspaces = workspaces

    def load_workspaces(self):
        return self._workspaces


def _workspace(root: Path, workspace_id="abcdef12", name="Gateway WS"):
    return SimpleNamespace(id=workspace_id, name=name, root_path=str(root))


def _patch_workspace_manager(monkeypatch, workspaces):
    manager = DummyManager(workspaces)
    monkeypatch.setattr("miminions.cli.gateway.WorkspaceManager", lambda config_dir: manager)
    monkeypatch.setattr("miminions.cli.gateway.get_config_dir", lambda: Path("unused"))
    return manager


def _job(
    job_id="job1",
    name="Job",
    schedule=None,
    enabled=True,
    message="hello from a scheduled job",
    status=None,
):
    return CronJob(
        id=job_id,
        name=name,
        enabled=enabled,
        schedule=schedule or CronSchedule(kind="every", every_ms=5000),
        payload=CronPayload(message=message),
        state=CronJobState(next_run_at_ms=1_800_000_000_000, last_status=status),
    )


def test_gateway_workspace_resolution_by_key_id_prefix_and_name(tmp_path):
    first = _workspace(tmp_path / "one", workspace_id="abcdef12", name="One")
    second = _workspace(tmp_path / "two", workspace_id="ab999999", name="Two")
    manager = DummyManager({"key": first, "other": second})

    resolved = _resolve_workspace(manager, "key")
    assert resolved is first, f"expect result to be {first}, got {resolved}"
    resolved = _resolve_workspace(manager, "abcdef12")
    assert resolved is first, f"expect result to be {first}, got {resolved}"
    resolved = _resolve_workspace(manager, "abc")
    assert resolved is first, f"expect result to be {first}, got {resolved}"
    resolved = _resolve_workspace(manager, "ab")
    assert resolved is None, f"expect result to be {None}, got {resolved}"
    resolved = _resolve_workspace(manager, "Two")
    assert resolved is second, f"expect result to be {second}, got {resolved}"
    empty_manager = DummyManager({})
    resolved = _resolve_workspace(empty_manager, "anything")
    assert resolved is None, f"expect result to be {None}, got {resolved}"
    resolved = _resolve_workspace(manager, "missing")
    assert resolved is None, f"expect result to be {None}, got {resolved}"


def test_gateway_workspace_lookup_errors(tmp_path, monkeypatch):
    missing_root = _workspace(tmp_path / "missing")
    no_root = SimpleNamespace(id="no-root", name="No Root", root_path=None)
    _patch_workspace_manager(monkeypatch, {missing_root.id: missing_root})

    with pytest.raises(Exception, match="root_path does not exist"):
        _get_workspace_or_raise(missing_root.id)

    _patch_workspace_manager(monkeypatch, {no_root.id: no_root})
    with pytest.raises(Exception, match="workspace init-files"):
        _get_workspace_or_raise(no_root.id)

    _patch_workspace_manager(monkeypatch, {})
    with pytest.raises(Exception, match="Workspace not found"):
        _get_workspace_or_raise("missing")


def test_gateway_paths_and_cron_service(tmp_path):
    workspace = _workspace(tmp_path)

    paths = _get_gateway_paths(workspace)
    service = _build_cron_service(workspace)

    assert paths == GatewayPaths(
        root=tmp_path.resolve(),
        sessions_path=tmp_path.resolve() / "sessions" / "gateway",
        cron_store_path=tmp_path.resolve() / "data" / "gateway" / "cron" / "jobs.json",
    ), f"expect result to be {GatewayPaths(root=tmp_path.resolve(), sessions_path=tmp_path.resolve() / 'sessions' / 'gateway', cron_store_path=tmp_path.resolve() / 'data' / 'gateway' / 'cron' / 'jobs.json')}, got {paths}"
    assert service.store_path == paths.cron_store_path, f"expect result to be {paths.cron_store_path}, got {service.store_path}"


def test_gateway_formatting_validation_and_confirmation_helpers(isolated_cli_runner):
    formatted_none = _format_ms_timestamp(None)
    assert formatted_none == "-", f"expect result to be {'-'}, got {formatted_none}"
    formatted_zero = _format_ms_timestamp(0)
    assert formatted_zero == "-", f"expect result to be {'-'}, got {formatted_zero}"
    formatted_future = _format_ms_timestamp(1_800_000_000_000)
    assert formatted_future.startswith("2027"), f"expect _format_ms_timestamp returns text starting with 2027, got {formatted_future}"
    parsed_ms = _parse_iso_datetime_to_ms("2026-05-05T09:00:00")
    assert parsed_ms > 0, f"expect _parse_iso_datetime_to_ms returns a positive timestamp, got {parsed_ms}"
    with pytest.raises(Exception, match="Expected ISO datetime"):
        _parse_iso_datetime_to_ms("not-a-date")

    preview = _message_preview("  many\n\nspaces   here  ")
    assert preview == "many spaces here", f"expect result to be {'many spaces here'}, got {preview}"
    preview = _message_preview("x" * 60, limit=10)
    assert preview == "xxxxxxx...", f"expect result to be {'xxxxxxx...'}, got {preview}"
    formatted_schedule = _format_schedule(_job(schedule=CronSchedule(kind="every", every_ms=2000)))
    assert formatted_schedule == "every 2s", f"expect result to be {'every 2s'}, got {formatted_schedule}"
    formatted_schedule = _format_schedule(_job(schedule=CronSchedule(kind="at", at_ms=1_800_000_000_000)))
    assert formatted_schedule.startswith("at 2027"), f"expect _format_schedule returns value starting with 'at 2027', got {formatted_schedule}"
    formatted_schedule = _format_schedule(_job(schedule=CronSchedule(kind="cron", expr="0 9 * * *", tz="UTC")))
    assert formatted_schedule == "cron 0 9 * * * (UTC)", f"expect result to be {'cron 0 9 * * * (UTC)'}, got {formatted_schedule}"
    formatted_schedule = _format_schedule(_job(schedule=SimpleNamespace(kind="custom")))
    assert formatted_schedule == "custom", f"expect result to be {'custom'}, got {formatted_schedule}"

    _validate_name_and_message(" name ", " message ")
    with pytest.raises(Exception, match="name cannot be empty"):
        _validate_name_and_message(" ", "message")
    with pytest.raises(Exception, match="message cannot be empty"):
        _validate_name_and_message("name", " ")

    _confirm_or_force("skip prompt", force=True)

    @click.command()
    def confirm_command():
        _confirm_or_force("Continue?", force=False)

    result = isolated_cli_runner.invoke(confirm_command, input="n\n")
    assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"


def test_echo_job_list_empty_and_populated(isolated_cli_runner):
    @click.command()
    def empty_command():
        _echo_job_list([])

    empty = isolated_cli_runner.invoke(empty_command)
    assert empty.exit_code == 0, f"expect cli exit code 0, got {empty.exit_code} with output: {empty.output}"
    assert "No cron jobs found." in empty.output, f"expect 'No cron jobs found.' in empty.output, got {empty.output}"

    jobs = [
        _job(
            job_id="long-job-id",
            name="A very long scheduled job name",
            schedule=CronSchedule(kind="cron", expr="*/5 * * * *"),
            enabled=False,
            message="this message should be shortened because it is too verbose",
            status="ok",
        )
    ]
    @click.command()
    def list_command():
        _echo_job_list(jobs)

    listed = isolated_cli_runner.invoke(list_command)
    assert listed.exit_code == 0, f"expect cli exit code 0, got {listed.exit_code} with output: {listed.output}"
    assert "ID        Name" in listed.output, f"expect 'ID        Name' in listed.output, got {listed.output}"
    assert "long-job-id" in listed.output, f"expect 'long-job-id' in listed.output, got {listed.output}"
    assert "A very long schedule" in listed.output, f"expect 'A very long schedule' in listed.output, got {listed.output}"
    assert "this message should be shortened" in listed.output, f"expect 'this message should be shortened' in listed.output, got {listed.output}"


def test_default_cron_handler_logs_and_returns_reason(caplog):
    job = _job(name="Nightly", message="run this scheduled gateway turn")

    result = asyncio.run(_default_cron_handler(job))

    assert result == "no handler configured", f"expect result to be {'no handler configured'}, got {result}"
    assert "gateway cron dispatch is not configured" in caplog.text, f"expect 'gateway cron dispatch is not configured' in caplog.text, got {caplog.text}"
    assert "Nightly" in caplog.text, f"expect 'Nightly' in caplog.text, got {caplog.text}"


def test_gateway_status_counts_sessions_and_jobs(tmp_path, monkeypatch, isolated_cli_runner):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})
    sessions_path = tmp_path / "sessions" / "gateway"
    session = SessionManager(sessions_path).get_or_create("cli:one")
    SessionManager(sessions_path).save(session)
    cron = _build_cron_service(workspace)
    cron.add_job("job", CronSchedule(kind="every", every_ms=1000), "hello")

    result = isolated_cli_runner.invoke(gateway_cli, ["status", "--workspace", workspace.id])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Workspace name: Gateway WS" in result.output, f"expect 'Workspace name: Gateway WS' in result.output, got {result.output}"
    assert "Number of sessions: 1" in result.output, f"expect 'Number of sessions: 1' in result.output, got {result.output}"
    assert "Number of cron jobs: 1" in result.output, f"expect 'Number of cron jobs: 1' in result.output, got {result.output}"


def test_gateway_cron_add_variants_and_list_filters(tmp_path, monkeypatch, isolated_cli_runner):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})

    every = isolated_cli_runner.invoke(
        gateway_cli,
        [
            "cron",
            "add-every",
            "--workspace",
            workspace.id,
            "--name",
            "seconds",
            "--every-seconds",
            "3",
            "--message",
            "ping",
        ],
    )
    assert every.exit_code == 0, f"expect cli exit code 0, got {every.exit_code} with output: {every.output}"
    assert "Added cron job" in every.output, f"expect 'Added cron job' in every.output, got {every.output}"

    at = isolated_cli_runner.invoke(
        gateway_cli,
        [
            "cron",
            "add-at",
            "--workspace",
            workspace.id,
            "--name",
            "once",
            "--at",
            "2026-05-05T09:00:00",
            "--message",
            "wake up",
        ],
    )
    assert at.exit_code == 0, f"expect cli exit code 0, got {at.exit_code} with output: {at.output}"

    service = _build_cron_service(workspace)
    jobs = service.list_jobs(include_disabled=True)
    service.enable_job(jobs[0].id, enabled=False)

    default_list = isolated_cli_runner.invoke(
        gateway_cli, ["cron", "list", "--workspace", workspace.id]
    )
    all_list = isolated_cli_runner.invoke(
        gateway_cli, ["cron", "list", "--workspace", workspace.id, "--all"]
    )

    assert "seconds" not in default_list.output, f"expect 'seconds' not in default_list.output, got {default_list.output}"
    assert "seconds" in all_list.output, f"expect 'seconds' in all_list.output, got {all_list.output}"
    assert "once" in all_list.output, f"expect 'once' in all_list.output, got {all_list.output}"


def test_gateway_cron_add_every_validation_errors(tmp_path, monkeypatch, isolated_cli_runner):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})

    multiple = isolated_cli_runner.invoke(
        gateway_cli,
        [
            "cron",
            "add-every",
            "--workspace",
            workspace.id,
            "--name",
            "bad",
            "--every-seconds",
            "1",
            "--every-minutes",
            "1",
            "--message",
            "hello",
        ],
    )
    assert multiple.exit_code != 0, f"expect cli exit code != 0, got {multiple.exit_code} with output: {multiple.output}"
    assert "Specify exactly one" in multiple.output, f"expect 'Specify exactly one' in multiple.output, got {multiple.output}"

    negative = isolated_cli_runner.invoke(
        gateway_cli,
        [
            "cron",
            "add-every",
            "--workspace",
            workspace.id,
            "--name",
            "bad",
            "--every-seconds",
            "0",
            "--message",
            "hello",
        ],
    )
    assert negative.exit_code != 0, f"expect cli exit code != 0, got {negative.exit_code} with output: {negative.output}"
    assert "interval must be positive" in negative.output, f"expect 'interval must be positive' in negative.output, got {negative.output}"


def test_gateway_cron_expression_dependency_and_value_error(
    tmp_path, monkeypatch, isolated_cli_runner
):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})
    monkeypatch.setattr(importlib.util, "find_spec", lambda name: None if name == "croniter" else object())

    missing_dependency = isolated_cli_runner.invoke(
        gateway_cli,
        [
            "cron",
            "add-cron",
            "--workspace",
            workspace.id,
            "--name",
            "cron",
            "--expr",
            "* * * * *",
            "--message",
            "hello",
        ],
    )
    assert missing_dependency.exit_code != 0, f"expect cli exit code != 0, got {missing_dependency.exit_code} with output: {missing_dependency.output}"
    assert "Cron expressions require croniter" in missing_dependency.output, f"expect 'Cron expressions require croniter' in missing_dependency.output, got {missing_dependency.output}"

    monkeypatch.setattr(importlib.util, "find_spec", lambda name: object())

    class BrokenCron:
        def add_job(self, **kwargs):
            raise ValueError("bad cron")

    monkeypatch.setattr("miminions.cli.gateway._build_cron_service", lambda workspace: BrokenCron())
    bad_value = isolated_cli_runner.invoke(
        gateway_cli,
        [
            "cron",
            "add-cron",
            "--workspace",
            workspace.id,
            "--name",
            "cron",
            "--expr",
            "* * * * *",
            "--message",
            "hello",
        ],
    )
    assert bad_value.exit_code != 0, f"expect cli exit code != 0, got {bad_value.exit_code} with output: {bad_value.output}"
    assert "bad cron" in bad_value.output, f"expect 'bad cron' in bad_value.output, got {bad_value.output}"


def test_gateway_cron_missing_job_paths(tmp_path, monkeypatch, isolated_cli_runner):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})

    for command, expected in (
        (["cron", "remove", "--workspace", workspace.id, "missing", "--force"], "Cron job not found"),
        (["cron", "enable", "--workspace", workspace.id, "missing"], "Cron job not found"),
        (["cron", "disable", "--workspace", workspace.id, "missing"], "Cron job not found"),
        (["cron", "run", "--workspace", workspace.id, "missing"], "Cron job not found or disabled"),
    ):
        result = isolated_cli_runner.invoke(gateway_cli, command)
        assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
        assert expected in result.output, f"expect {expected} in result.output, got {result.output}"


def test_gateway_cron_run_disabled_requires_force(tmp_path, monkeypatch, isolated_cli_runner):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})
    service = _build_cron_service(workspace)
    job = service.add_job("job", CronSchedule(kind="every", every_ms=1000), "hello")
    service.enable_job(job.id, enabled=False)

    blocked = isolated_cli_runner.invoke(
        gateway_cli, ["cron", "run", "--workspace", workspace.id, job.id]
    )
    forced = isolated_cli_runner.invoke(
        gateway_cli, ["cron", "run", "--workspace", workspace.id, job.id, "--force"]
    )

    assert blocked.exit_code != 0, f"expect cli exit code != 0, got {blocked.exit_code} with output: {blocked.output}"
    assert "not found or disabled" in blocked.output, f"expect 'not found or disabled' in blocked.output, got {blocked.output}"
    assert forced.exit_code == 0, f"expect cli exit code 0, got {forced.exit_code} with output: {forced.output}"
    target_value = f"Ran cron job: {job.id}"
    assert target_value in forced.output, f"expect {target_value} in forced.output, got {forced.output}"


def test_gateway_sessions_list_show_delete_paths(tmp_path, monkeypatch, isolated_cli_runner):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})
    manager = SessionManager(tmp_path / "sessions" / "gateway")
    session = manager.get_or_create("cli:default")
    session.add_message("system", "ignored leading system")
    session.add_message("user", "hello")
    session.add_message("assistant", "hi")
    manager.save(session)

    listed = isolated_cli_runner.invoke(
        gateway_cli, ["sessions", "list", "--workspace", workspace.id, "--show-path"]
    )
    assert listed.exit_code == 0, f"expect cli exit code 0, got {listed.exit_code} with output: {listed.output}"
    assert "cli:default" in listed.output, f"expect 'cli:default' in listed.output, got {listed.output}"
    assert ".jsonl" in listed.output, f"expect '.jsonl' in listed.output, got {listed.output}"

    limited = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "show", "--workspace", workspace.id, "cli:default", "--limit", "1"],
    )
    assert limited.exit_code == 0, f"expect cli exit code 0, got {limited.exit_code} with output: {limited.output}"
    assert "[assistant] hi" in limited.output, f"expect '[assistant] hi' in limited.output, got {limited.output}"
    assert "[user] hello" not in limited.output, f"expect '[user] hello' not in limited.output, got {limited.output}"

    full = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "show", "--workspace", workspace.id, "cli:default", "--full"],
    )
    assert "[system] ignored leading system" in full.output, f"expect '[system] ignored leading system' in full.output, got {full.output}"
    assert "[user] hello" in full.output, f"expect '[user] hello' in full.output, got {full.output}"

    bad_limit = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "show", "--workspace", workspace.id, "cli:default", "--limit", "0"],
    )
    assert bad_limit.exit_code != 0, f"expect cli exit code != 0, got {bad_limit.exit_code} with output: {bad_limit.output}"
    assert "limit must be positive" in bad_limit.output, f"expect 'limit must be positive' in bad_limit.output, got {bad_limit.output}"

    cancelled = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "delete", "--workspace", workspace.id, "cli:default"],
        input="n\n",
    )
    assert cancelled.exit_code != 0, f"expect cli exit code != 0, got {cancelled.exit_code} with output: {cancelled.output}"
    remaining_sessions = list((tmp_path / "sessions" / "gateway").glob("*.jsonl"))
    assert remaining_sessions, f"expect session delete cancellation keeps session jsonl files on disk, got {remaining_sessions}"

    deleted = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "delete", "--workspace", workspace.id, "cli:default", "--force"],
    )
    assert deleted.exit_code == 0, f"expect cli exit code 0, got {deleted.exit_code} with output: {deleted.output}"
    assert "Deleted session: cli:default" in deleted.output, f"expect 'Deleted session: cli:default' in deleted.output, got {deleted.output}"


def test_gateway_sessions_show_empty_and_missing_delete(
    tmp_path, monkeypatch, isolated_cli_runner
):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})
    manager = SessionManager(tmp_path / "sessions" / "gateway")
    manager.save(manager.get_or_create("empty"))

    empty = isolated_cli_runner.invoke(
        gateway_cli, ["sessions", "show", "--workspace", workspace.id, "empty"]
    )
    missing_delete = isolated_cli_runner.invoke(
        gateway_cli, ["sessions", "delete", "--workspace", workspace.id, "missing", "--force"]
    )

    assert empty.exit_code == 0, f"expect cli exit code 0, got {empty.exit_code} with output: {empty.output}"
    assert "No messages found." in empty.output, f"expect 'No messages found.' in empty.output, got {empty.output}"
    assert missing_delete.exit_code != 0, f"expect cli exit code != 0, got {missing_delete.exit_code} with output: {missing_delete.output}"
    assert "Session not found: missing" in missing_delete.output, f"expect 'Session not found: missing' in missing_delete.output, got {missing_delete.output}"


def test_gateway_run_starts_and_stops_runtime(tmp_path, monkeypatch, isolated_cli_runner):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})
    calls = []

    class FakeRuntime:
        def __init__(self, channel_manager, cron_service=None):
            calls.append(("init", cron_service is None))

        async def start(self):
            calls.append(("start", None))

        async def shutdown(self):
            calls.append(("shutdown", None))

    async def fake_sleep(_seconds):
        raise KeyboardInterrupt

    monkeypatch.setattr("miminions.cli.gateway.LocalGatewayRuntime", FakeRuntime)
    monkeypatch.setattr("miminions.cli.gateway.asyncio.sleep", fake_sleep)

    result = isolated_cli_runner.invoke(
        gateway_cli,
        ["run", "--workspace", workspace.id, "--no-cron", "--log-level", "bogus"],
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Gateway running." in result.output, f"expect 'Gateway running.' in result.output, got {result.output}"
    assert "Gateway stopped." in result.output, f"expect 'Gateway stopped.' in result.output, got {result.output}"
    assert calls == [("init", True), ("start", None), ("shutdown", None)], f"expect result to be {[('init', True), ('start', None), ('shutdown', None)]}, got {calls}"
