from pathlib import Path
from types import SimpleNamespace

from click.testing import CliRunner

from miminions.interface.cli.chat import chat_command
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
        "miminions.interface.cli.chat.WorkspaceManager",
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

    monkeypatch.setattr(
        "miminions.interface.cli.chat.WorkspaceManager",
        lambda config_dir: manager,
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

    assert result.exit_code == 0, f"Expected exit code 0, but got {result.exit_code}"
    assert "Session:" in result.output, f"Expected 'Session:' in output, but got: {result.output}"
    assert "assistant reply" in result.output, f"Expected 'assistant reply' in output, but got: {result.output}"

    sessions_dir = tmp_path / "sessions"
    session_files = list(sessions_dir.glob("*.jsonl"))
    assert len(session_files) == 1, f"Expected 1 session file, but found {len(session_files)}"

    contents = session_files[0].read_text(encoding="utf-8")
    assert '"role": "user"' in contents, f"Expected 'role' to be in the contents, but got: {contents}"
    assert '"content": "hello"' in contents, f"Expected 'content' to be in the contents, but got: {contents}"
    assert '"role": "assistant"' in contents, f"Expected 'role: assistant' in contents, but got: {contents}"
    assert '"content": "assistant reply"' in contents, f"Expected 'content: assistant reply' in contents, but got: {contents}"