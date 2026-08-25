from pathlib import Path
from types import SimpleNamespace

from miminions.cli.chat import chat_command
from miminions.workspace_fs import init_workspace


NONEXISTENT_WORKSPACE_REF = "workspace-does-not-exist"


def _assert_exit_code(result, expected: int, behavior: str) -> None:
    assert result.exit_code == expected, f"expect cli exit code {expected}, got {result.exit_code} with output: {result.output}"


class MockStore:
    loaded_session_ids = []

    def __init__(self, root):
        self.root = Path(root)
        self.records = []

    def create_session_id(self):
        return "created-session"

    def load_as_pydantic_messages(self, session_id):
        self.loaded_session_ids.append(session_id)
        return ["history"]

    def append(self, session_id, role, content, meta=None):
        self.records.append((session_id, role, content, meta))


class MockMinion:
    def __init__(self, replies=None, fail=False):
        self._last_messages = ["after"]
        self._model = None
        self.replies = replies or ["assistant reply"]
        self.fail = fail
        self.context = None

    def set_context(self, workspace, root):
        self.context = (workspace, root)

    async def run(self, text, message_history=None):
        if self.fail:
            raise RuntimeError("model failed")
        return self.replies.pop(0)


def test_chat_uses_default_workspace_and_records_session(tmp_path, isolated_cli_runner, monkeypatch):
    """Chat should use the configured default workspace and persist the conversation."""
    init_workspace(tmp_path)
    workspace = SimpleNamespace(id="ws1", name="Default", root_path=str(tmp_path))
    manager = SimpleNamespace(load_workspaces=lambda: {"ws1": workspace})
    distill_calls = []

    monkeypatch.setattr("miminions.cli.chat.get_config", lambda: {"default_workspace": "ws1"})
    monkeypatch.setattr("miminions.cli.chat.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("miminions.cli.chat.WorkspaceManager", lambda config_dir: manager)
    monkeypatch.setattr("miminions.cli.chat.JsonlSessionStore", MockStore)
    monkeypatch.setattr("miminions.cli.chat.create_minion", lambda **kwargs: MockMinion())
    monkeypatch.setattr(
        "miminions.cli.chat._run_session_distillation",
        lambda **kwargs: distill_calls.append(kwargs),
    )

    result = isolated_cli_runner.invoke(chat_command, [], input="hello\n/quit\n")

    _assert_exit_code(result, 0, "starting chat with the default workspace")
    assert "Workspace : Default" in result.output, f"expect 'Workspace : Default' in result.output, got {result.output}"
    assert "Session   : created-session" in result.output, f"expect 'Session   : created-session' in result.output, got {result.output}"
    assert "assistant reply" in result.output, f"expect 'assistant reply' in result.output, got {result.output}"
    assert len(distill_calls) == 1, f"expect result to be {1}, got {len(distill_calls)}"


def test_chat_errors_when_no_workspace_or_default_is_configured(isolated_cli_runner, monkeypatch):
    """Starting chat without --workspace should fail if no default workspace is configured."""
    monkeypatch.setattr("miminions.cli.chat.get_config", lambda: {})

    no_default = isolated_cli_runner.invoke(chat_command, [])

    assert no_default.exit_code != 0, f"expect cli exit code != 0, got {no_default.exit_code} with output: {no_default.output}"
    assert "No --workspace given" in no_default.output, f"expect 'No --workspace given' in no_default.output, got {no_default.output}"


def test_chat_errors_when_workspace_ref_does_not_resolve(
    isolated_cli_runner, tmp_path, monkeypatch
):
    """A workspace ref that is absent from storage should produce a clear error."""
    manager = SimpleNamespace(load_workspaces=lambda: {})
    monkeypatch.setattr("miminions.cli.chat.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("miminions.cli.chat.WorkspaceManager", lambda config_dir: manager)

    result = isolated_cli_runner.invoke(
        chat_command, ["--workspace", NONEXISTENT_WORKSPACE_REF]
    )

    assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
    target_value = f"Workspace not found: {NONEXISTENT_WORKSPACE_REF}"
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"


def test_chat_resumes_session_and_turn_errors_are_logged(
    tmp_path, isolated_cli_runner, monkeypatch
):
    """Model turn failures should be captured as assistant error messages in the session log."""
    init_workspace(tmp_path)
    MockStore.loaded_session_ids = []
    workspace = SimpleNamespace(id="ws1", name="Default", root_path=str(tmp_path))
    manager = SimpleNamespace(load_workspaces=lambda: {"ws1": workspace})
    store_instances = []

    def store_factory(root):
        store = MockStore(root)
        store_instances.append(store)
        return store

    monkeypatch.setattr("miminions.cli.chat.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("miminions.cli.chat.WorkspaceManager", lambda config_dir: manager)
    monkeypatch.setattr("miminions.cli.chat.JsonlSessionStore", store_factory)
    monkeypatch.setattr("miminions.cli.chat.create_minion", lambda **kwargs: MockMinion(fail=True))
    monkeypatch.setattr("miminions.cli.chat._run_session_distillation", lambda **kwargs: None)

    result = isolated_cli_runner.invoke(
        chat_command,
        ["--workspace", "ws1", "--session", "existing"],
        input="hello\n/quit\n",
    )

    _assert_exit_code(result, 0, "resuming a chat session with a model failure")
    assert "Session   : existing" in result.output, f"expect 'Session   : existing' in result.output, got {result.output}"
    assert "[error] RuntimeError: model failed" in result.output, f"expect '[error] RuntimeError: model failed' in result.output, got {result.output}"
    assert MockStore.loaded_session_ids == ["existing"], f"expect result to be {['existing']}, got {MockStore.loaded_session_ids}"
    expected_record = (
        "existing",
        "assistant",
        "[error] RuntimeError: model failed",
        {"source": "cli-chat"},
    )
    records = store_instances[0].records
    assert expected_record in records, f"expect expected_record in store_instances[0].records, got {records}"


def test_chat_distillation_warning_only(tmp_path, isolated_cli_runner, monkeypatch):
    """Distillation failures should warn without failing the completed chat session."""
    init_workspace(tmp_path)
    workspace = SimpleNamespace(id="ws1", name="Default", root_path=str(tmp_path))
    manager = SimpleNamespace(load_workspaces=lambda: {"ws1": workspace})

    monkeypatch.setattr("miminions.cli.chat.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("miminions.cli.chat.WorkspaceManager", lambda config_dir: manager)
    monkeypatch.setattr("miminions.cli.chat.JsonlSessionStore", MockStore)
    monkeypatch.setattr("miminions.cli.chat.create_minion", lambda **kwargs: MockMinion())

    def fail_distillation(**kwargs):
        raise RuntimeError("distiller down")

    monkeypatch.setattr("miminions.cli.chat._run_session_distillation", fail_distillation)

    result = isolated_cli_runner.invoke(
        chat_command,
        ["--workspace", "ws1"],
        input="/quit\n",
    )

    _assert_exit_code(result, 0, "ending chat when distillation fails")
    assert "Warning: memory distillation skipped: distiller down" in result.output, f"expect 'Warning: memory distillation skipped: distiller down' in result.output, got {result.output}"
