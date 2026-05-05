import json
from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from miminions.core.gateway import SessionManager
from miminions.interface.cli.main import cli


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
        "miminions.interface.cli.gateway.WorkspaceManager",
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

    assert result.exit_code == 0
    assert "status" in result.output
    assert "cron" in result.output
    assert "sessions" in result.output


def test_gateway_status_requires_root_path(monkeypatch):
    workspace = SimpleNamespace(id="ws1", name="Test WS", root_path=None)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(cli, ["gateway", "status", "--workspace", "ws1"])

    assert result.exit_code != 0
    assert "workspace init-files" in result.output.lower()


def test_gateway_status_works(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(cli, ["gateway", "status", "--workspace", "ws1"])

    assert result.exit_code == 0, result.output
    assert "Workspace name: Test WS" in result.output
    assert "Gateway session storage path" in result.output
    assert "Cron job storage path" in result.output


def test_gateway_cron_list_empty(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(
        cli, ["gateway", "cron", "list", "--workspace", "ws1"]
    )

    assert result.exit_code == 0, result.output
    assert "No cron jobs found." in result.output


def test_gateway_cron_add_every_creates_jobs_json(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = _add_every(CliRunner())

    assert result.exit_code == 0, result.output
    jobs_path = tmp_path / "data" / "gateway" / "cron" / "jobs.json"
    assert jobs_path.exists()
    data = json.loads(jobs_path.read_text(encoding="utf-8"))
    job = data["jobs"][0]
    assert job["name"] == "test"
    assert job["schedule"]["kind"] == "every"
    assert job["schedule"]["everyMs"] == 300000
    assert job["payload"]["message"] == "hello"


def test_gateway_cron_remove_requires_confirmation_and_force(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)
    runner = CliRunner()
    assert _add_every(runner).exit_code == 0
    job_id = _job_id(tmp_path)

    cancelled = runner.invoke(
        cli,
        ["gateway", "cron", "remove", "--workspace", "ws1", job_id],
        input="n\n",
    )
    assert cancelled.exit_code != 0
    data = json.loads(
        (tmp_path / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(data["jobs"]) == 1

    removed = runner.invoke(
        cli,
        ["gateway", "cron", "remove", "--workspace", "ws1", job_id, "--force"],
    )
    assert removed.exit_code == 0, removed.output
    data = json.loads(
        (tmp_path / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["jobs"] == []


def test_gateway_cron_enable_disable(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)
    runner = CliRunner()
    assert _add_every(runner).exit_code == 0
    job_id = _job_id(tmp_path)

    disabled = runner.invoke(
        cli, ["gateway", "cron", "disable", "--workspace", "ws1", job_id]
    )
    assert disabled.exit_code == 0, disabled.output
    data = json.loads(
        (tmp_path / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["jobs"][0]["enabled"] is False

    enabled = runner.invoke(
        cli, ["gateway", "cron", "enable", "--workspace", "ws1", job_id]
    )
    assert enabled.exit_code == 0, enabled.output
    data = json.loads(
        (tmp_path / "data" / "gateway" / "cron" / "jobs.json").read_text(
            encoding="utf-8"
        )
    )
    assert data["jobs"][0]["enabled"] is True


def test_gateway_sessions_list_empty(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(
        cli, ["gateway", "sessions", "list", "--workspace", "ws1"]
    )

    assert result.exit_code == 0, result.output
    assert "No sessions found." in result.output


def test_gateway_sessions_show_missing(tmp_path, monkeypatch):
    workspace = _workspace(tmp_path)
    _patch_gateway_manager(monkeypatch, workspace)

    result = CliRunner().invoke(
        cli, ["gateway", "sessions", "show", "--workspace", "ws1", "missing"]
    )

    assert result.exit_code != 0
    assert "Session not found: missing" in result.output


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

    assert result.exit_code == 0, result.output
    assert not list(sessions_path.glob("*.jsonl"))