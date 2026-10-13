"""Interactive chat is a frontend to per-turn execution tasks."""

from unittest.mock import Mock

import click
import pytest
from click.testing import CliRunner

from miminions.cli.chat import chat_command
from miminions.core.workspace import WorkspaceManager, ensure_workspace


@pytest.fixture
def chat_setup(tmp_path, monkeypatch):
    home = tmp_path / "home"
    manager = WorkspaceManager(home)
    workspace = manager.create_workspace("Chat")
    workspace.root_path = str(tmp_path / "workspace")
    manager.save_workspaces({workspace.id: workspace})
    ensure_workspace(manager, workspace.id, init_files=True)
    monkeypatch.setattr("miminions.cli.chat.get_config_dir", lambda: home)
    monkeypatch.setattr("miminions.cli.chat.load_config", lambda: {"default_workspace": workspace.id})
    dispatch = Mock()
    monkeypatch.setattr("miminions.cli.dispatch.submit_task", dispatch)
    return workspace, dispatch


def test_default_workspace_turn_tasks_and_one_finalization(chat_setup):
    workspace, dispatch = chat_setup
    result = CliRunner().invoke(chat_command, [], input="hello\n\nsecond\n/quit\n")
    assert result.exit_code == 0, result.output
    assert "Workspace : Chat" in result.stdout
    calls = dispatch.call_args_list
    assert [call.args[0] for call in calls] == ["chat_turn", "chat_turn", "session_distill"]
    assert [calls[i].args[1]["prompt"] for i in range(2)] == ["hello", "second"]
    assert len({call.kwargs["session_key"] for call in calls}) == 1
    assert calls[0].args[1]["workspace"] == workspace.id
    assert calls[-1].kwargs["detach"] is True


def test_resume_session_and_empty_chat_does_not_distill(chat_setup):
    _, dispatch = chat_setup
    result = CliRunner().invoke(chat_command, ["--session", "existing"], input="/exit\n")
    assert result.exit_code == 0
    assert "Session   : existing" in result.output
    dispatch.assert_not_called()


def test_failed_turn_can_continue(chat_setup):
    _, dispatch = chat_setup
    dispatch.side_effect = [click.exceptions.Exit(1), None, None]
    result = CliRunner().invoke(chat_command, [], input="bad\ngood\n/quit\n")
    assert result.exit_code == 0
    assert [c.args[0] for c in dispatch.call_args_list] == ["chat_turn", "chat_turn", "session_distill"]


def test_interrupted_turn_exits_and_queues_finalization(chat_setup):
    _, dispatch = chat_setup
    dispatch.side_effect = [click.exceptions.Exit(130), None]
    result = CliRunner().invoke(chat_command, [], input="hello\n")
    assert result.exit_code == 130
    assert [c.args[0] for c in dispatch.call_args_list] == ["chat_turn", "session_distill"]
    assert dispatch.call_args.kwargs["detach"] is True


def test_missing_default_workspace(monkeypatch):
    monkeypatch.setattr("miminions.cli.chat.load_config", lambda: {})
    result = CliRunner().invoke(chat_command, [])
    assert result.exit_code == 1
    assert "no default workspace" in result.output


def test_missing_workspace(chat_setup):
    _, dispatch = chat_setup
    result = CliRunner().invoke(chat_command, ["--workspace", "missing"])
    assert result.exit_code == 1
    assert "Workspace not found" in result.output
    dispatch.assert_not_called()
