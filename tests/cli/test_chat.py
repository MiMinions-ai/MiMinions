from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from miminions.interface.cli.chat import chat_command
from miminions.workspace_fs.bootstrap import init_workspace


class DummyManager:
    def __init__(self, workspace):
        self._workspace = workspace

    def list_workspaces(self):
        return [self._workspace]


def test_chat_cli_requires_root_path(monkeypatch):
    workspace = SimpleNamespace(id="ws1", name="Test WS", root_path=None)
    manager = DummyManager(workspace)

    monkeypatch.setattr(
        "miminions.interface.cli.chat.WorkspaceManager",
        lambda: manager,
    )

    runner = CliRunner()
    result = runner.invoke(chat_command, ["--workspace", "ws1"])

    assert result.exit_code != 0
    assert "workspace init-files" in result.output.lower()


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

    monkeypatch.setattr(
        "miminions.interface.cli.chat.WorkspaceManager",
        lambda: manager,
    )
    monkeypatch.setattr(
        "miminions.interface.cli.chat._run_agent",
        lambda user_text, context, workspace, session_id: "assistant reply",
    )

    runner = CliRunner()
    result = runner.invoke(
        chat_command,
        ["--workspace", "ws1"],
        input="hello\nquit\n",
    )

    assert result.exit_code == 0
    assert "Session:" in result.output
    assert "assistant reply" in result.output

    sessions_dir = tmp_path / "sessions"
    session_files = list(sessions_dir.glob("*.jsonl"))
    assert len(session_files) == 1

    contents = session_files[0].read_text(encoding="utf-8")
    assert '"role": "user"' in contents
    assert '"content": "hello"' in contents
    assert '"role": "assistant"' in contents
    assert '"content": "assistant reply"' in contents