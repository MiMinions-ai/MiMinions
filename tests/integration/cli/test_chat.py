from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

from click.testing import CliRunner

from miminions.cli.chat import chat_command
from miminions.workspace_fs.bootstrap import init_workspace


def test_chat_cli_requires_root_path(monkeypatch):
    workspace = SimpleNamespace(id="ws1", name="Test WS", root_path=None)
    manager = MagicMock()
    manager.load_workspaces.return_value = {workspace.id: workspace}

    monkeypatch.setattr(
        "miminions.cli.chat.WorkspaceManager",
        lambda config_dir: manager,
    )

    runner = CliRunner()
    result = runner.invoke(chat_command, ["--workspace", "ws1"])

    assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
    output_lower = result.output.lower()
    assert "workspace init-files" in output_lower, f"expect contains 'workspace init-files', got {output_lower}"


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
    manager = MagicMock()
    manager.load_workspaces.return_value = {workspace.id: workspace}

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run_stream(self, *args, **kwargs):
            yield "assistant reply"

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
        input="hello\n/quit\n",
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Session   :" in result.output, f"expect contains 'Session   :', got {result.output}"
    assert "assistant reply" in result.output, f"expect contains 'assistant reply', got {result.output}"

    sessions_dir = tmp_path / "sessions"
    session_files = list(sessions_dir.glob("*.jsonl"))
    session_file_count = len(session_files)
    assert session_file_count == 1, f"expect chat session creates exactly one session jsonl file as 1, got {session_file_count}"

    contents = session_files[0].read_text(encoding="utf-8")
    assert '"role": "user"' in contents, f"expect contains '\"role\": \"user\"', got {contents}"
    assert '"content": "hello"' in contents, f"expect contains '\"content\": \"hello\"', got {contents}"
    assert '"role": "assistant"' in contents, f"expect contains '\"role\": \"assistant\"', got {contents}"
    assert '"content": "assistant reply"' in contents, f"expect contains '\"content\": \"assistant reply\"', got {contents}"


def test_chat_cli_streams_deltas_incrementally(tmp_path: Path, monkeypatch):
    init_workspace(tmp_path)

    workspace = SimpleNamespace(
        id="ws1",
        name="Test WS",
        root_path=str(tmp_path),
        nodes=[],
        rules=[],
        state={},
    )
    manager = MagicMock()
    manager.load_workspaces.return_value = {workspace.id: workspace}

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run_stream(self, *args, **kwargs):
            yield "foo"
            yield "bar"

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
        input="hello\n/quit\n",
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "foobar" in result.output, f"expect contains 'foobar', got {result.output}"

    contents = next((tmp_path / "sessions").glob("*.jsonl")).read_text(encoding="utf-8")
    assert '"content": "foobar"' in contents, f"expect contains '\"content\": \"foobar\"', got {contents}"


def test_chat_cli_persists_partial_reply_on_mid_stream_error(tmp_path: Path, monkeypatch):
    init_workspace(tmp_path)

    workspace = SimpleNamespace(
        id="ws1",
        name="Test WS",
        root_path=str(tmp_path),
        nodes=[],
        rules=[],
        state={},
    )
    manager = MagicMock()
    manager.load_workspaces.return_value = {workspace.id: workspace}

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run_stream(self, *args, **kwargs):
            yield "partial text"
            raise RuntimeError("stream died")

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
        input="hello\n/quit\n",
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "[error] RuntimeError: stream died" in result.output, f"expect contains '[error] RuntimeError: stream died', got {result.output}"

    contents = next((tmp_path / "sessions").glob("*.jsonl")).read_text(encoding="utf-8")
    assert "partial text" in contents, f"expect contains 'partial text', got {contents}"
    assert "[error] RuntimeError: stream died" in contents, f"expect contains '[error] RuntimeError: stream died', got {contents}"


def test_chat_cli_verbose_wires_hooks_into_minion(tmp_path: Path, monkeypatch):
    init_workspace(tmp_path)

    workspace = SimpleNamespace(
        id="ws1",
        name="Test WS",
        root_path=str(tmp_path),
        nodes=[],
        rules=[],
        state={},
    )
    manager = MagicMock()
    manager.load_workspaces.return_value = {workspace.id: workspace}

    captured_kwargs = {}

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run_stream(self, *args, **kwargs):
            yield "assistant reply"

    def _capturing_create_minion(*args, **kwargs):
        captured_kwargs.update(kwargs)
        return MockMinion()

    monkeypatch.setattr(
        "miminions.cli.chat.WorkspaceManager",
        lambda config_dir: manager,
    )
    monkeypatch.setattr(
        "miminions.cli.chat.create_minion",
        _capturing_create_minion,
    )

    runner = CliRunner()
    result = runner.invoke(
        chat_command,
        ["--workspace", "ws1", "--verbose"],
        input="/quit\n",
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    on_tool_call_is_callable = callable(captured_kwargs["on_tool_call"])
    assert on_tool_call_is_callable, f"expect create_minion receives callable on_tool_call in verbose mode, got {on_tool_call_is_callable}"
    on_turn_end_is_callable = callable(captured_kwargs["on_turn_end"])
    assert on_turn_end_is_callable, f"expect create_minion receives callable on_turn_end in verbose mode, got {on_turn_end_is_callable}"

    captured_kwargs.clear()
    result = runner.invoke(
        chat_command,
        ["--workspace", "ws1"],
        input="/quit\n",
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert captured_kwargs["on_tool_call"] is None, f"expect non-verbose chat creates minion with on_tool_call callback as None, got {captured_kwargs['on_tool_call']}"
    assert captured_kwargs["on_turn_end"] is None, f"expect non-verbose chat creates minion with on_turn_end callback as None, got {captured_kwargs['on_turn_end']}"


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
    manager = MagicMock()
    manager.load_workspaces.return_value = {workspace.id: workspace}

    calls = []

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run_stream(self, *args, **kwargs):
            yield "assistant reply"

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
        input="hello\n/quit\n",
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    call_count = len(calls)
    assert call_count == 1, f"expect chat exit runs session distillation exactly once as 1, got {call_count}"
    assert calls[0][0] == "ws1", f"expect distillation receives workspace id from active chat workspace as 'ws1', got {calls[0][0]}"
    assert calls[0][1] == tmp_path, f"expect tmp_path, got {calls[0][1]}"
    session_id_value = calls[0][2]
    assert session_id_value, f"expect distillation call includes a non-empty session_id, got {session_id_value}"


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
    manager = MagicMock()
    manager.load_workspaces.return_value = {workspace.id: workspace}

    class MockMinion:
        def __init__(self, *args, **kwargs):
            self._last_messages = []
            self._model = None
        def set_context(self, *args, **kwargs):
            pass
        async def run_stream(self, *args, **kwargs):
            yield "assistant reply"

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
        input="/quit\n",
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Warning: memory distillation skipped" in result.output, f"expect contains 'Warning: memory distillation skipped', got {result.output}"