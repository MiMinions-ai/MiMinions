import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from miminions.core.gateway import SessionManager
from miminions.cli.main import cli


class DummyManager:
    def __init__(self, workspaces):
        self._workspaces = workspaces

    def load_workspaces(self):
        return self._workspaces


def _workspace(tmp_path: Path, workspace_id: str = "ws1", name: str = "Test WS"):
    return SimpleNamespace(id=workspace_id, name=name, root_path=str(tmp_path))


def _patch_gateway_manager(monkeypatch, workspace):
    manager = DummyManager({workspace.id: workspace})
    monkeypatch.setattr(
        "miminions.cli.gateway.WorkspaceManager",
        lambda config_dir: manager,
    )
    return manager


def _add_every(runner, workspace_ref="ws1", name="test", message="hello"):
    return runner.invoke(
        cli,
        [
            "gateway",
            "cron",
            "add-every",
            "--workspace",
            workspace_ref,
            "--name",
            name,
            "--every-minutes",
            "5",
            "--message",
            message,
        ],
    )


def _job_id(root: Path) -> str:
    data = json.loads(
        (root / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    return data["jobs"][0]["id"]


def test_gateway_cli_registration():
    result = CliRunner().invoke(cli, ["gateway", "--help"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "status" in result.output, f"expect contains 'status', got {result.output}"
    assert "cron" in result.output, f"expect contains 'cron', got {result.output}"
    assert "sessions" in result.output, f"expect contains 'sessions', got {result.output}"


def test_gateway_status_requires_root_path(monkeypatch):
    workspace = SimpleNamespace(id="ws1", name="Test WS", root_path=None)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(cli, ["gateway", "status", "--workspace", "ws1"])

    assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
    output_lower = result.output.lower()
    assert "workspace init-files" in output_lower, f"expect contains 'workspace init-files', got {output_lower}"


def test_gateway_status_works(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(cli, ["gateway", "status", "--workspace", "ws1"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Workspace name: Test WS" in result.output, f"expect contains 'Workspace name: Test WS', got {result.output}"
    assert "Gateway session storage path" in result.output, f"expect contains 'Gateway session storage path', got {result.output}"
    assert "Cron job storage path" in result.output, f"expect contains 'Cron job storage path', got {result.output}"


def test_gateway_cron_list_empty(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(
        cli, ["gateway", "cron", "list", "--workspace", "ws1"]
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "No cron jobs found." in result.output, f"expect contains 'No cron jobs found.', got {result.output}"


def test_gateway_cron_add_every_creates_jobs_json(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)
    runner = CliRunner()

    result = _add_every(runner)

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    jobs_path = tmp_path / "data" / "gateway" / "cron" / "jobs.json"
    jobs_file_exists = jobs_path.exists()
    assert jobs_file_exists, f"expect add-every creates cron jobs.json file as True, got {jobs_file_exists}"
    data = json.loads(jobs_path.read_text(encoding="utf-8"))
    job = data["jobs"][0]
    assert job["name"] == "test", f"expect cron add-every stores provided job name in persisted schedule record as 'test', got {job['name']}"
    assert job["schedule"]["kind"] == "every", f"expect cron add-every persists schedule kind as 'every', got {job['schedule']['kind']}"
    assert job["schedule"]["everyMs"] == 300000, f"expect cron add-every stores 5-minute schedule interval in milliseconds as 300000, got {job['schedule']['everyMs']}"
    assert job["payload"]["message"] == "hello", f"expect cron add-every stores provided payload message text in job payload as 'hello', got {job['payload']['message']}"


def test_gateway_cron_remove_requires_confirmation_and_force(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)
    runner = CliRunner()
    add_result = _add_every(runner)
    assert add_result.exit_code == 0, f"expect cli exit code 0, got {add_result.exit_code} with output: {add_result.output}"
    job_id = _job_id(tmp_path)

    cancelled = runner.invoke(
        cli,
        ["gateway", "cron", "remove", "--workspace", "ws1", job_id],
        input="n\n",
    )
    assert cancelled.exit_code != 0, f"expect cli exit code != 0, got {cancelled.exit_code} with output: {cancelled.output}"
    data = json.loads(
        (tmp_path / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    jobs_count = len(data["jobs"])
    assert jobs_count == 1, f"expect non-force remove cancellation keeps existing cron job untouched in storage as 1, got {jobs_count}"

    removed = runner.invoke(
        cli,
        ["gateway", "cron", "remove", "--workspace", "ws1", job_id, "--force"],
    )
    assert removed.exit_code == 0, f"expect cli exit code 0, got {removed.exit_code} with output: {removed.output}"
    data = json.loads(
        (tmp_path / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["jobs"] == [], f"expect force remove deletes target cron job from persistent store as [], got {data['jobs']}"


def test_gateway_cron_enable_disable(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)
    runner = CliRunner()
    add_result = _add_every(runner)
    assert add_result.exit_code == 0, f"expect cli exit code 0, got {add_result.exit_code} with output: {add_result.output}"
    job_id = _job_id(tmp_path)

    disabled = runner.invoke(
        cli, ["gateway", "cron", "disable", "--workspace", "ws1", job_id]
    )
    assert disabled.exit_code == 0, f"expect cli exit code 0, got {disabled.exit_code} with output: {disabled.output}"
    data = json.loads(
        (tmp_path / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["jobs"][0]["enabled"] is False, f"expect cron disable command persists enabled flag as False, got {data['jobs'][0]['enabled']}"

    enabled = runner.invoke(
        cli, ["gateway", "cron", "enable", "--workspace", "ws1", job_id]
    )
    assert enabled.exit_code == 0, f"expect cli exit code 0, got {enabled.exit_code} with output: {enabled.output}"
    data = json.loads(
        (tmp_path / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["jobs"][0]["enabled"] is True, f"expect cron enable command persists enabled flag as True, got {data['jobs'][0]['enabled']}"


def test_gateway_sessions_list_empty(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(
        cli, ["gateway", "sessions", "list", "--workspace", "ws1"]
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "No sessions found." in result.output, f"expect contains 'No sessions found.', got {result.output}"


def test_gateway_sessions_show_missing(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(
        cli, ["gateway", "sessions", "show", "--workspace", "ws1", "missing"]
    )

    assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
    assert "Session not found: missing" in result.output, f"expect contains 'Session not found: missing', got {result.output}"


def test_gateway_sessions_delete_force(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)
    sessions_path = tmp_path / "sessions" / "gateway"
    manager = SessionManager(sessions_path)
    session = manager.get_or_create("cli:default")
    session.add_message("user", "hello")
    manager.save(session)

    result = CliRunner().invoke(
        cli,
        [
            "gateway",
            "sessions",
            "delete",
            "--workspace",
            "ws1",
            "cli:default",
            "--force",
        ],
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    remaining_sessions = list(sessions_path.glob("*.jsonl"))
    assert not remaining_sessions, f"expect session delete removes all session jsonl files as False, got {remaining_sessions}"
