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

    assert _resolve_workspace(manager, "key") is first
    assert _resolve_workspace(manager, "abcdef12") is first
    assert _resolve_workspace(manager, "abc") is first
    assert _resolve_workspace(manager, "ab") is None
    assert _resolve_workspace(manager, "Two") is second
    assert _resolve_workspace(DummyManager({}), "anything") is None
    assert _resolve_workspace(manager, "missing") is None


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
    )
    assert service.store_path == paths.cron_store_path


def test_gateway_formatting_validation_and_confirmation_helpers(isolated_cli_runner):
    assert _format_ms_timestamp(None) == "-"
    assert _format_ms_timestamp(0) == "-"
    assert _format_ms_timestamp(1_800_000_000_000).startswith("2027")
    assert _parse_iso_datetime_to_ms("2026-05-05T09:00:00") > 0
    with pytest.raises(Exception, match="Expected ISO datetime"):
        _parse_iso_datetime_to_ms("not-a-date")

    assert _message_preview("  many\n\nspaces   here  ") == "many spaces here"
    assert _message_preview("x" * 60, limit=10) == "xxxxxxx..."
    assert _format_schedule(_job(schedule=CronSchedule(kind="every", every_ms=2000))) == "every 2s"
    assert _format_schedule(_job(schedule=CronSchedule(kind="at", at_ms=1_800_000_000_000))).startswith("at 2027")
    assert _format_schedule(_job(schedule=CronSchedule(kind="cron", expr="0 9 * * *", tz="UTC"))) == "cron 0 9 * * * (UTC)"
    assert _format_schedule(_job(schedule=SimpleNamespace(kind="custom"))) == "custom"

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
    assert result.exit_code != 0


def test_echo_job_list_empty_and_populated(isolated_cli_runner):
    @click.command()
    def empty_command():
        _echo_job_list([])

    empty = isolated_cli_runner.invoke(empty_command)
    assert empty.exit_code == 0
    assert "No cron jobs found." in empty.output

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
    assert listed.exit_code == 0
    assert "ID        Name" in listed.output
    assert "long-job-id" in listed.output
    assert "A very long schedule" in listed.output
    assert "this message should be shortened" in listed.output


def test_default_cron_handler_logs_and_returns_reason(caplog):
    job = _job(name="Nightly", message="run this scheduled gateway turn")

    result = asyncio.run(_default_cron_handler(job))

    assert result == "no handler configured"
    assert "gateway cron dispatch is not configured" in caplog.text
    assert "Nightly" in caplog.text


def test_gateway_status_counts_sessions_and_jobs(tmp_path, monkeypatch, isolated_cli_runner):
    workspace = _workspace(tmp_path)
    _patch_workspace_manager(monkeypatch, {workspace.id: workspace})
    sessions_path = tmp_path / "sessions" / "gateway"
    session = SessionManager(sessions_path).get_or_create("cli:one")
    SessionManager(sessions_path).save(session)
    cron = _build_cron_service(workspace)
    cron.add_job("job", CronSchedule(kind="every", every_ms=1000), "hello")

    result = isolated_cli_runner.invoke(gateway_cli, ["status", "--workspace", workspace.id])

    assert result.exit_code == 0
    assert "Workspace name: Gateway WS" in result.output
    assert "Number of sessions: 1" in result.output
    assert "Number of cron jobs: 1" in result.output


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
    assert every.exit_code == 0
    assert "Added cron job" in every.output

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
    assert at.exit_code == 0

    service = _build_cron_service(workspace)
    jobs = service.list_jobs(include_disabled=True)
    service.enable_job(jobs[0].id, enabled=False)

    default_list = isolated_cli_runner.invoke(
        gateway_cli, ["cron", "list", "--workspace", workspace.id]
    )
    all_list = isolated_cli_runner.invoke(
        gateway_cli, ["cron", "list", "--workspace", workspace.id, "--all"]
    )

    assert "seconds" not in default_list.output
    assert "seconds" in all_list.output
    assert "once" in all_list.output


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
    assert multiple.exit_code != 0
    assert "Specify exactly one" in multiple.output

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
    assert negative.exit_code != 0
    assert "interval must be positive" in negative.output


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
    assert missing_dependency.exit_code != 0
    assert "Cron expressions require croniter" in missing_dependency.output

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
    assert bad_value.exit_code != 0
    assert "bad cron" in bad_value.output


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
        assert result.exit_code != 0
        assert expected in result.output


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

    assert blocked.exit_code != 0
    assert "not found or disabled" in blocked.output
    assert forced.exit_code == 0
    assert f"Ran cron job: {job.id}" in forced.output


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
    assert listed.exit_code == 0
    assert "cli:default" in listed.output
    assert ".jsonl" in listed.output

    limited = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "show", "--workspace", workspace.id, "cli:default", "--limit", "1"],
    )
    assert limited.exit_code == 0
    assert "[assistant] hi" in limited.output
    assert "[user] hello" not in limited.output

    full = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "show", "--workspace", workspace.id, "cli:default", "--full"],
    )
    assert "[system] ignored leading system" in full.output
    assert "[user] hello" in full.output

    bad_limit = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "show", "--workspace", workspace.id, "cli:default", "--limit", "0"],
    )
    assert bad_limit.exit_code != 0
    assert "limit must be positive" in bad_limit.output

    cancelled = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "delete", "--workspace", workspace.id, "cli:default"],
        input="n\n",
    )
    assert cancelled.exit_code != 0
    assert list((tmp_path / "sessions" / "gateway").glob("*.jsonl"))

    deleted = isolated_cli_runner.invoke(
        gateway_cli,
        ["sessions", "delete", "--workspace", workspace.id, "cli:default", "--force"],
    )
    assert deleted.exit_code == 0
    assert "Deleted session: cli:default" in deleted.output


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

    assert empty.exit_code == 0
    assert "No messages found." in empty.output
    assert missing_delete.exit_code != 0
    assert "Session not found: missing" in missing_delete.output


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

    assert result.exit_code == 0
    assert "Gateway running." in result.output
    assert "Gateway stopped." in result.output
    assert calls == [("init", True), ("start", None), ("shutdown", None)]
