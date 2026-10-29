"""Project selection through the real CLI and shared execution handler."""

import json
from unittest.mock import Mock

import pytest
from click.testing import CliRunner
from pydantic_ai.models.test import TestModel
from pydantic_ai.messages import SystemPromptPart

from miminions.agent import create_minion
from miminions.cli.chat import chat_command
from miminions.cli.prompt import ask_prompt
from miminions.cli.project import select_project
from miminions.context.context_builder import ContextBuilder
from miminions.core.workspace import WorkspaceManager, ensure_workspace
from miminions.execution import ExecutionRequest
from miminions.execution.handlers import TaskContext, get_handler
from miminions.execution.models import conversation_key
from miminions.execution.store import ExecutionStore


@pytest.fixture
def project_cli(tmp_path, monkeypatch):
    home = tmp_path / "home"
    project = tmp_path / "project"
    project.mkdir()
    (project / "main.py").write_text("def generate_report(path: str):\n    '''Generate a CSV report.'''\n    return path", encoding="utf-8")
    monkeypatch.chdir(project)
    monkeypatch.setenv("MIMINIONS_HOME", str(home))
    dispatch = Mock()
    monkeypatch.setattr("miminions.cli.dispatch.submit_task", dispatch)
    monkeypatch.setattr("miminions.cli.prompt.submit_task", dispatch)
    return home, project, dispatch


def test_chat_detects_project_shows_capabilities_without_calling_model(project_cli):
    home, project, dispatch = project_cli
    before = set(project.iterdir())
    result = CliRunner().invoke(chat_command, [], input="/quit\n")
    assert result.exit_code == 0, result.output
    assert "Found 1 callable Python functions" in result.output
    assert "Generate a CSV report" in result.output
    assert "Help me use generate_report" in result.output
    dispatch.assert_not_called()
    assert set(project.iterdir()) == before
    workspaces = WorkspaceManager(home).load_workspaces()
    assert len(workspaces) == 1
    workspace = next(iter(workspaces.values()))
    assert workspace.state["project_root"] == str(project)
    assert (home / "workspaces" / f"ws_{workspace.id}" / "discovery.json").exists()


def test_chat_submits_and_resumes_same_project_session(project_cli):
    home, _, dispatch = project_cli
    result = CliRunner().invoke(chat_command, ["--session", "known"], input="help\n/exit\n")
    assert result.exit_code == 0, result.output
    first = dispatch.call_args_list[0]
    second = CliRunner().invoke(chat_command, ["--session", "known"], input="continue\n/exit\n")
    assert second.exit_code == 0, second.output
    assert dispatch.call_args_list[2].kwargs["session_key"] == first.kwargs["session_key"]
    assert len(WorkspaceManager(home).load_workspaces()) == 1


def test_prompt_detects_project_and_preserves_attachment_options(project_cli):
    home, project, dispatch = project_cli
    result = CliRunner().invoke(ask_prompt, ["--detach", "generate", "report"])
    assert result.exit_code == 0, result.output
    assert dispatch.call_args.kwargs["detach"]
    params = dispatch.call_args.args[1]
    assert params["prompt"] == "generate report"
    workspace = WorkspaceManager(home).load_workspaces()[params["workspace"]]
    assert workspace.state["project_root"] == str(project)
    assert not (project / "sessions").exists()


@pytest.mark.parametrize("command,args", [(chat_command, []), (ask_prompt, ["hello"])])
@pytest.mark.parametrize("conflict", [["--workspace", "default"], ["--no-discovery"]])
def test_conflicting_options_fail_before_creating_project_state(project_cli, command, args, conflict):
    home, project, dispatch = project_cli
    result = CliRunner().invoke(command, ["--project", str(project), *conflict, *args])
    assert result.exit_code == 2, result.output
    assert "cannot be combined" in result.output
    assert not (home / "workspaces.json").exists()
    dispatch.assert_not_called()


def test_explicit_workspace_and_opt_out_preserve_existing_workflow(project_cli, monkeypatch):
    home, _, dispatch = project_cli
    manager = WorkspaceManager(home)
    workspace = manager.create_workspace("Configured")
    workspace.root_path = str(home / "existing")
    manager.save_workspaces({workspace.id: workspace})
    ensure_workspace(manager, workspace.id, init_files=True)
    monkeypatch.setattr("miminions.cli.chat.load_config", lambda: {"default_workspace": workspace.id})
    for args in (["--workspace", workspace.id], ["--no-discovery"]):
        result = CliRunner().invoke(chat_command, args, input="hello\n/quit\n")
        assert result.exit_code == 0, result.output
        assert "Found " not in result.output
        assert dispatch.call_args_list[-2].args[1]["workspace"] == workspace.id
    assert len(manager.load_workspaces()) == 1
    result = CliRunner().invoke(ask_prompt, ["--no-discovery", "hello"])
    assert result.exit_code == 0, result.output
    saved = manager.load_workspaces()[dispatch.call_args.args[1]["workspace"]]
    assert saved.name == "default" and "project_root" not in saved.state


def test_explicit_project_works_outside_project_and_nonproject_falls_back(project_cli, tmp_path, monkeypatch):
    home, project, dispatch = project_cli
    elsewhere = tmp_path / "elsewhere"
    elsewhere.mkdir()
    monkeypatch.chdir(elsewhere)
    result = CliRunner().invoke(ask_prompt, ["--project", str(project), "hello"])
    assert result.exit_code == 0, result.output
    project_id = dispatch.call_args.args[1]["workspace"]
    result = CliRunner().invoke(ask_prompt, ["hello"])
    assert result.exit_code == 0, result.output
    default_id = dispatch.call_args.args[1]["workspace"]
    assert default_id != project_id
    assert WorkspaceManager(home).load_workspaces()[default_id].name == "default"


async def test_handler_builds_project_tools_context_and_persists_checkpoint(project_cli, monkeypatch):
    home, project, _ = project_cli
    workspace_id = select_project(home, None, project, False, init_files=True)
    workspace, root = ensure_workspace(WorkspaceManager(home), workspace_id)
    agents = []
    def factory(**kwargs):
        agent = create_minion(**kwargs, model=TestModel(call_tools=["workspace_search_tools"]))
        agents.append(agent)
        return agent
    monkeypatch.setattr("miminions.agent.create_minion", factory)
    store = ExecutionStore(home)
    key = conversation_key(workspace_id, "project-session")
    task_id = store.enqueue(ExecutionRequest("prompt", {"workspace": workspace_id, "session_id": "project-session",
                                                       "prompt": "What reports can this project generate?"}, session_key=key))
    context = TaskContext(store, store.claim())
    await get_handler("prompt")(context)
    assert "workspace_search_tools" in agents[0].list_tools()
    assert store.checkpoint(key)
    assert not store.approvals(task_id)
    records = [json.loads(line) for line in (root / "sessions/project-session.jsonl").read_text().splitlines()]
    assert [r["role"] for r in records] == ["user", "assistant"]
    prompt = ContextBuilder(global_top_k=0).build(workspace, root, project_context=agents[0]._project_context)
    assert "## Project Context" in prompt and str(project) in prompt
    assert "separate project directory" in prompt and "workspace_search_tools" in prompt
    # Resumed native histories must refresh the project section, not retain the first scan forever.
    store.finish(task_id, "completed")
    (project / "main.py").write_text(
        "def generate_report(path: str):\n    '''UPDATED project capability.'''\n    return path", encoding="utf-8",
    )
    store.enqueue(ExecutionRequest("chat_turn", {"workspace": workspace_id, "session_id": "project-session",
                                                "prompt": "What changed?"}, session_key=key))
    await get_handler("chat_turn")(TaskContext(store, store.claim()))
    system = [part.content for message in agents[-1]._last_messages for part in message.parts
              if isinstance(part, SystemPromptPart)]
    assert any("UPDATED project capability" in text for text in system)


def test_project_paths_are_canonical_and_isolated(tmp_path):
    home = tmp_path / "home"
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    one = select_project(home, None, first, False)
    alias = select_project(home, None, first / ".." / "first", False)
    two = select_project(home, None, second, False)
    assert one == alias and one != two
