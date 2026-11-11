"""Project API credentials remain private and scoped to their execution task."""

import os
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from miminions.agent.provider import ModelFactory
from miminions.core.workspace import Workspace, WorkspaceManager
from miminions.execution import ExecutionRequest
from miminions.execution.environment import PROVIDER_KEYS, provider_environment, provider_env_path
from miminions.execution.handlers import TaskContext, get_handler
from miminions.execution.store import ExecutionStore


@pytest.fixture
def task_context(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    for name in PROVIDER_KEYS:
        monkeypatch.delenv(name, raising=False)
    return SimpleNamespace(params={}, store=SimpleNamespace(home=tmp_path / "state"),
                           task=SimpleNamespace(request=ExecutionRequest("prompt", cwd=str(tmp_path))))


def test_provider_credentials_load_before_model_construction_and_are_restored(task_context, tmp_path):
    (tmp_path / ".env").write_text("\ufeff# Local credentials\nexport OPENROUTER_API_KEY='fake-project-key'\n", encoding="utf-8")
    with provider_environment(task_context):
        assert os.environ["OPENROUTER_API_KEY"] == "fake-project-key"
        assert ModelFactory.create("openrouter") is not None
    assert "OPENROUTER_API_KEY" not in os.environ


def test_existing_exported_key_takes_precedence(task_context, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-exported-key")
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=fake-project-key\n", encoding="utf-8")
    with provider_environment(task_context):
        assert os.environ["OPENROUTER_API_KEY"] == "fake-exported-key"
    assert os.environ["OPENROUTER_API_KEY"] == "fake-exported-key"


def test_empty_export_is_filled_and_restored(task_context, tmp_path, monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "")
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=fake-project-key\n", encoding="utf-8")
    with provider_environment(task_context):
        assert os.environ["OPENROUTER_API_KEY"] == "fake-project-key"
    assert os.environ["OPENROUTER_API_KEY"] == ""


def test_only_provider_keys_are_loaded(task_context, tmp_path, monkeypatch):
    monkeypatch.setenv("MIMINIONS_HOME", str(tmp_path / "original"))
    (tmp_path / ".env").write_text(
        "OPENROUTER_API_KEY=fake-router\nOPENAI_API_KEY=fake-openai\nANTHROPIC_API_KEY=fake-anthropic\n"
        "GEMINI_API_KEY=fake-gemini\nGOOGLE_API_KEY=fake-google\n"
        "MIMINIONS_HOME=wrong-home\nUNRELATED_SETTING=do-not-load\n", encoding="utf-8",
    )
    with provider_environment(task_context):
        assert all(os.environ.get(name) for name in PROVIDER_KEYS)
        assert os.environ["MIMINIONS_HOME"] == str(tmp_path / "original")
        assert "UNRELATED_SETTING" not in os.environ
    assert all(name not in os.environ for name in PROVIDER_KEYS)


def test_selected_project_wins_over_launch_directory_and_no_discovery(task_context, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("OPENROUTER_API_KEY=fake-selected-project\n", encoding="utf-8")
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=fake-launch-directory\n", encoding="utf-8")
    workspace = Workspace(name="project")
    workspace.state["project_root"] = str(project)
    WorkspaceManager(task_context.store.home).save_workspaces({workspace.id: workspace})
    task_context.params.update(workspace=workspace.id, no_discovery=True)
    assert provider_env_path(task_context) == project / ".env"
    with provider_environment(task_context):
        assert os.environ["OPENROUTER_API_KEY"] == "fake-selected-project"


def test_missing_project_file_does_not_fall_back_to_unrelated_launch_file(task_context, tmp_path):
    project = tmp_path / "project"
    project.mkdir()
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=fake-unrelated-project\n", encoding="utf-8")
    workspace = Workspace(name="project", state={"project_root": str(project)})
    WorkspaceManager(task_context.store.home).save_workspaces({workspace.id: workspace})
    task_context.params["workspace"] = workspace.id
    with provider_environment(task_context):
        assert "OPENROUTER_API_KEY" not in os.environ


def test_captured_directory_is_used_without_searching_parents(task_context, tmp_path):
    child = tmp_path / "child"
    child.mkdir()
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=fake-parent-key\n", encoding="utf-8")
    task_context.task.request = ExecutionRequest("prompt", cwd=str(child))
    with provider_environment(task_context):
        assert "OPENROUTER_API_KEY" not in os.environ


def test_key_rotation_and_distinct_projects_do_not_leak(task_context, tmp_path):
    for index in range(3):
        key = f"fake-rotated-key-{index}"
        (tmp_path / ".env").write_text(f"OPENROUTER_API_KEY={key}\n", encoding="utf-8")
        with provider_environment(task_context):
            assert os.environ["OPENROUTER_API_KEY"] == key
        assert "OPENROUTER_API_KEY" not in os.environ
    other = tmp_path / "other"
    other.mkdir()
    task_context.task.request = ExecutionRequest("prompt", cwd=str(other))
    with provider_environment(task_context):
        assert "OPENROUTER_API_KEY" not in os.environ


def test_missing_key_error_identifies_file_and_powershell_setup(task_context, tmp_path):
    with pytest.raises(ValueError, match="CLI credential file") as captured:
        with provider_environment(task_context):
            ModelFactory.create("openrouter")
    assert str(tmp_path / ".env") in str(captured.value)
    assert "PowerShell" in str(captured.value)


@pytest.mark.parametrize("failure", [PermissionError("fake-secret-in-error"), UnicodeError("fake-secret-in-error")])
def test_unreadable_dotenv_errors_do_not_echo_contents(task_context, monkeypatch, failure):
    monkeypatch.setattr(Path, "open", Mock(side_effect=failure))
    with pytest.raises(ValueError, match="Cannot read provider API credentials") as captured:
        with provider_environment(task_context):
            pass
    assert "fake-secret-in-error" not in str(captured.value)


async def test_handler_and_distillation_load_credentials_without_persisting_them(task_context, tmp_path, monkeypatch):
    secret = "fake-private-sentinel-never-persist"
    (tmp_path / ".env").write_text(f"OPENROUTER_API_KEY={secret}\n", encoding="utf-8")
    store = ExecutionStore(tmp_path / "state")
    calls = []
    async def handler(context):
        assert os.environ["OPENROUTER_API_KEY"] == secret
        assert ModelFactory.create("openrouter") is not None
        context.phase("Model configured")
        calls.append(context.task.request.kind)
    from miminions.execution import handlers
    for kind in ("chat_turn", "prompt", "session_distill"):
        monkeypatch.setitem(handlers._HANDLERS, kind, handler)
        task_id = store.enqueue(ExecutionRequest(kind, cwd=str(tmp_path)))
        await get_handler(kind)(TaskContext(store, store.claim()))
        store.finish(task_id, "completed")
        assert "OPENROUTER_API_KEY" not in os.environ
        assert secret not in str([event.to_dict() for event in store.events(task_id)])
        assert secret not in str(store.get(task_id).to_dict())
    assert calls == ["chat_turn", "prompt", "session_distill"]
    assert secret.encode() not in store.path.read_bytes()


def test_failed_task_restores_loaded_credentials(task_context, tmp_path):
    (tmp_path / ".env").write_text("OPENROUTER_API_KEY=fake-key\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="task failed"):
        with provider_environment(task_context):
            raise RuntimeError("task failed")
    assert "OPENROUTER_API_KEY" not in os.environ
