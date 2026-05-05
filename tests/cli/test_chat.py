from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from miminions.cli.chat import chat_command
from miminions.workspace_fs.bootstrap import init_workspace


class DummyManager:
    def __init__(self, workspace):
        self._workspace = workspace

    def load_workspaces(self):
        return {self._workspace.id: self._workspace}


def test_chat_cli_requires_root_path(monkeypatch):
    workspace = SimpleNamespace(id="ws1", name="Test WS", root_path=None)
    manager = DummyManager(workspace)

    monkeypatch.setattr(
        "miminions.cli.chat.WorkspaceManager",
        lambda config_dir: manager,
    )

    runner = CliRunner()
    result = runner.invoke(chat_command, ["--workspace", "ws1"])

    assert result.exit_code != 0, f"Expected non-zero exit code, but got {result.exit_code}"
    assert "workspace init-files" in result.output.lower(), f"Expected 'workspace init-files' in the output, but got: {result.output}"


def test_chat_cli_creates_session_and_logs_messages(tmp_path: Path, monkeypatch):
    init_workspace(tmp_path)

    workspace = SimpleNamespace(
        id="ws1",
        name="Test WS",
        root_path=str(tmp_path),
        nodes=[],
        rules=[],
        state={},
    )
    manager = DummyManager(workspace)

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run(self, *args, **kwargs):
            return "assistant reply"

    monkeypatch.setattr(
        "miminions.cli.chat.WorkspaceManager",
        lambda config_dir: manager,
    )
    monkeypatch.setattr(
        "miminions.cli.chat.create_minion",
        lambda *args, **kwargs: MockMinion()
    )

    runner = CliRunner()
    result = runner.invoke(
        chat_command,
        ["--workspace", "ws1"],
        input="hello\nquit\n",
    )

    assert result.exit_code == 0, f"Expected exit code 0, but got {result.exit_code}"
    assert "Session   :" in result.output, f"Expected 'Session   :' in output, but got: {result.output}"
    assert "assistant reply" in result.output, f"Expected 'assistant reply' in output, but got: {result.output}"

    sessions_dir = tmp_path / "sessions"
    session_files = list(sessions_dir.glob("*.jsonl"))
    assert len(session_files) == 1, f"Expected 1 session file, but found {len(session_files)}"

    contents = session_files[0].read_text(encoding="utf-8")
    assert '"role": "user"' in contents, f"Expected 'role' to be in the contents, but got: {contents}"
    assert '"content": "hello"' in contents, f"Expected 'content' to be in the contents, but got: {contents}"
    assert '"role": "assistant"' in contents, f"Expected 'role: assistant' in contents, but got: {contents}"
    assert '"content": "assistant reply"' in contents, f"Expected 'content: assistant reply' in contents, but got: {contents}"


def test_chat_cli_runs_distillation_once_on_exit(tmp_path: Path, monkeypatch):
    init_workspace(tmp_path)

    workspace = SimpleNamespace(
        id="ws1",
        name="Test WS",
        root_path=str(tmp_path),
        nodes=[],
        rules=[],
        state={},
    )
    manager = DummyManager(workspace)

    calls = []

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run(self, *args, **kwargs):
            return "assistant reply"

    monkeypatch.setattr(
        "miminions.cli.chat.WorkspaceManager",
        lambda config_dir: manager,
    )
    monkeypatch.setattr(
        "miminions.cli.chat.create_minion",
        lambda *args, **kwargs: MockMinion()
    )
    monkeypatch.setattr(
        "miminions.cli.chat._run_session_distillation",
        lambda workspace, root, session_id, model=None: calls.append((workspace.id, root, session_id)),
    )

    runner = CliRunner()
    result = runner.invoke(
        chat_command,
        ["--workspace", "ws1"],
        input="hello\nquit\n",
    )

    assert result.exit_code == 0
    assert len(calls) == 1
    assert calls[0][0] == "ws1"
    assert calls[0][1] == tmp_path
    assert calls[0][2]


def test_chat_cli_distillation_error_is_warning_only(tmp_path: Path, monkeypatch):
    init_workspace(tmp_path)

    workspace = SimpleNamespace(
        id="ws1",
        name="Test WS",
        root_path=str(tmp_path),
        nodes=[],
        rules=[],
        state={},
    )
    manager = DummyManager(workspace)

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run(self, *args, **kwargs):
            return "assistant reply"

    monkeypatch.setattr(
        "miminions.cli.chat.WorkspaceManager",
        lambda config_dir: manager,
    )
    monkeypatch.setattr(
        "miminions.cli.chat.create_minion",
        lambda *args, **kwargs: MockMinion()
    )

    def _boom(*_args, **_kwargs):
        raise RuntimeError("distiller unavailable")

    monkeypatch.setattr("miminions.cli.chat._run_session_distillation", _boom)

    runner = CliRunner()
    result = runner.invoke(
        chat_command,
        ["--workspace", "ws1"],
        input="quit\n",
    )

    assert result.exit_code == 0
    assert "Warning: memory distillation skipped" in result.output