from pathlib import Path
from types import SimpleNamespace

from miminions.cli.chat import chat_command
from miminions.workspace_fs import init_workspace


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

    assert result.exit_code == 0
    assert "Workspace : Default" in result.output
    assert "Session   : created-session" in result.output
    assert "assistant reply" in result.output
    assert len(distill_calls) == 1


def test_chat_errors_for_missing_default_or_workspace(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.chat.get_config", lambda: {})

    no_default = isolated_cli_runner.invoke(chat_command, [])
    assert no_default.exit_code != 0
    assert "No --workspace given" in no_default.output

    manager = SimpleNamespace(load_workspaces=lambda: {})
    monkeypatch.setattr("miminions.cli.chat.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("miminions.cli.chat.WorkspaceManager", lambda config_dir: manager)

    missing = isolated_cli_runner.invoke(chat_command, ["--workspace", "missing"])
    assert missing.exit_code != 0
    assert "Workspace not found: missing" in missing.output


def test_chat_resumes_session_and_turn_errors_are_logged(
    tmp_path, isolated_cli_runner, monkeypatch
):
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

    assert result.exit_code == 0
    assert "Session   : existing" in result.output
    assert "[error] RuntimeError: model failed" in result.output
    assert MockStore.loaded_session_ids == ["existing"]
    assert ("existing", "assistant", "[error] RuntimeError: model failed", {"source": "cli-chat"}) in store_instances[0].records


def test_chat_distillation_warning_only(tmp_path, isolated_cli_runner, monkeypatch):
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

    assert result.exit_code == 0
    assert "Warning: memory distillation skipped: distiller down" in result.output
