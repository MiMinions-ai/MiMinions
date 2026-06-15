import json
from pathlib import Path

from click.testing import CliRunner

from miminions.cli.main import cli
from miminions.core.workspace import Workspace, WorkspaceManager
from miminions.workspace_fs.bootstrap import init_workspace


class MockMinion:
    def __init__(self, name="MiMinions"):
        self.name = name
        self._last_messages = []
        self._model = None

    def set_context(self, *args, **kwargs):
        pass

    def register_tool(self, *args, **kwargs):
        pass

    async def run(self, *args, **kwargs):
        return f"{self.name} reply"


def _patch_runtime(monkeypatch, tmp_path: Path, calls: list[str] | None = None):
    config_dir = tmp_path / "config"
    workspaces_root = tmp_path / "workspaces"

    monkeypatch.setattr("miminions.cli.chat.get_config_dir", lambda: config_dir)
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: config_dir)
    monkeypatch.setattr(
        "miminions.core.workspace.DEFAULT_WORKSPACES_ROOT",
        workspaces_root,
    )
    monkeypatch.setattr(
        "miminions.cli.chat._run_session_distillation",
        lambda *args, **kwargs: None,
    )

    def create_default_minion(*args, **kwargs):
        name = kwargs.get("name", "MiMinions")
        if calls is not None:
            calls.append(name)
        return MockMinion(name)

    monkeypatch.setattr("miminions.cli.chat.create_minion", create_default_minion)
    monkeypatch.setattr("miminions.cli.agent.create_minion", create_default_minion)
    return config_dir, workspaces_root


def _workspace_data(config_dir: Path) -> dict:
    return json.loads((config_dir / "workspaces.json").read_text(encoding="utf-8"))


def test_start_creates_default_workspace_and_opens_chat(tmp_path: Path, monkeypatch):
    config_dir, workspaces_root = _patch_runtime(monkeypatch, tmp_path)

    result = CliRunner().invoke(cli, ["start"], input="/quit\n")

    assert result.exit_code == 0, result.output
    assert "Workspace : default" in result.output
    data = _workspace_data(config_dir)
    workspace_id = next(iter(data))
    assert data[workspace_id]["name"] == "default"
    assert (workspaces_root / f"ws_{workspace_id}" / "sessions").exists()


def test_start_resumes_existing_session_id(tmp_path: Path, monkeypatch):
    config_dir, workspaces_root = _patch_runtime(monkeypatch, tmp_path)
    manager = WorkspaceManager(config_dir)
    workspace = manager.create_workspace("default")
    root = workspaces_root / f"ws_{workspace.id}"
    init_workspace(root)
    workspace.root_path = str(root)
    manager.save_workspaces({workspace.id: workspace})
    session_path = root / "sessions" / "known-session.jsonl"
    session_path.write_text("", encoding="utf-8")

    result = CliRunner().invoke(
        cli,
        ["start", "--session-id", "known-session"],
        input="/quit\n",
    )

    assert result.exit_code == 0, result.output
    assert "Session   : known-session" in result.output


def test_start_missing_session_warns_and_creates_new_session(tmp_path: Path, monkeypatch):
    _patch_runtime(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        cli,
        ["start", "--session-id", "missing-session"],
        input="/quit\n",
    )

    assert result.exit_code == 0, result.output
    assert "Warning: session 'missing-session' not found" in result.output
    assert "Session   : missing-session" not in result.output


def test_start_agent_resolves_by_id_and_name(tmp_path: Path, monkeypatch):
    config_dir, _workspaces_root = _patch_runtime(monkeypatch, tmp_path, calls=[])
    config_dir.mkdir(parents=True, exist_ok=True)
    (config_dir / "agents.json").write_text(
        json.dumps(
            {
                "helper": {
                    "name": "Helper Agent",
                    "description": "Helps",
                    "type": "general",
                }
            }
        ),
        encoding="utf-8",
    )

    calls: list[str] = []
    _patch_runtime(monkeypatch, tmp_path, calls=calls)

    by_id = CliRunner().invoke(cli, ["start", "--agent", "helper"], input="/quit\n")
    by_name = CliRunner().invoke(
        cli,
        ["start", "--agent", "Helper Agent"],
        input="/quit\n",
    )

    assert by_id.exit_code == 0, by_id.output
    assert by_name.exit_code == 0, by_name.output
    assert calls.count("Helper Agent") == 2


def test_start_missing_agent_warns_and_uses_default(tmp_path: Path, monkeypatch):
    calls: list[str] = []
    _patch_runtime(monkeypatch, tmp_path, calls=calls)

    result = CliRunner().invoke(
        cli,
        ["start", "--agent", "does-not-exist"],
        input="/quit\n",
    )

    assert result.exit_code == 0, result.output
    assert "Warning: agent 'does-not-exist' not found" in result.output
    assert "MiMinions" in calls


def test_start_workspace_resolves_by_id_name_and_initializes(tmp_path: Path, monkeypatch):
    config_dir, workspaces_root = _patch_runtime(monkeypatch, tmp_path)
    manager = WorkspaceManager(config_dir)
    workspace = manager.create_workspace("ready")
    manager.save_workspaces({workspace.id: workspace})

    by_name = CliRunner().invoke(cli, ["start", "--workspace", "ready"], input="/quit\n")
    by_id = CliRunner().invoke(
        cli,
        ["start", "--workspace", workspace.id[:8]],
        input="/quit\n",
    )

    assert by_name.exit_code == 0, by_name.output
    assert by_id.exit_code == 0, by_id.output
    assert "Workspace : ready" in by_name.output
    assert (workspaces_root / f"ws_{workspace.id}" / "sessions").exists()


def test_start_workspace_existing_path_creates_or_reuses_workspace(tmp_path: Path, monkeypatch):
    config_dir, _workspaces_root = _patch_runtime(monkeypatch, tmp_path)
    root = tmp_path / "custom-root"
    root.mkdir()

    first = CliRunner().invoke(
        cli,
        ["start", "--workspace", str(root)],
        input="/quit\n",
    )
    second = CliRunner().invoke(
        cli,
        ["start", "--workspace", str(root)],
        input="/quit\n",
    )

    assert first.exit_code == 0, first.output
    assert second.exit_code == 0, second.output
    assert (root / "sessions").exists()
    data = _workspace_data(config_dir)
    assert len(data) == 1
    assert next(iter(data.values()))["root_path"] == str(root.resolve())


def test_start_missing_workspace_warns_and_uses_default(tmp_path: Path, monkeypatch):
    _patch_runtime(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        cli,
        ["start", "--workspace", "does-not-exist"],
        input="/quit\n",
    )

    assert result.exit_code == 0, result.output
    assert "Warning: workspace 'does-not-exist' not found" in result.output
    assert "Workspace : default" in result.output


def test_start_background_spawns_gateway_and_writes_pid(tmp_path: Path, monkeypatch):
    _patch_runtime(monkeypatch, tmp_path)
    popen_calls = []

    class FakeProcess:
        pid = 4242

    def fake_popen(*args, **kwargs):
        popen_calls.append((args, kwargs))
        return FakeProcess()

    monkeypatch.setattr("miminions.cli.start.subprocess.Popen", fake_popen)

    result = CliRunner().invoke(cli, ["start", "--background"])

    assert result.exit_code == 0, result.output
    assert "Gateway PID : 4242" in result.output
    command = popen_calls[0][0][0]
    assert command[1:5] == ["-m", "miminions", "gateway", "run"]
    assert "--workspace" in command

    workspace = next(iter(_workspace_data(tmp_path / "config").values()))
    root = Path(workspace["root_path"])
    assert (root / "data" / "gateway" / "server.pid").read_text(
        encoding="utf-8"
    ) == "4242"
    assert str(root / "data" / "gateway" / "server.log") in result.output
