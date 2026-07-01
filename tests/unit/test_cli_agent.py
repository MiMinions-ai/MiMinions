import json
from types import SimpleNamespace

from miminions.cli.agent import (
    _execute_prompt_with_tool_fallback,
    _extract_first_two_ints,
    agent_cli,
    load_agents,
    save_agents,
)


def test_agent_storage_helpers_and_integer_extraction(tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)

    assert load_agents() == {}
    save_agents({"agent1": {"name": "Agent One"}})
    assert load_agents() == {"agent1": {"name": "Agent One"}}

    assert _extract_first_two_ints("add -3 and 14 please") == (-3, 14)
    assert _extract_first_two_ints("only one 7") is None


def test_agent_add_list_update_goal_remove(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)

    added = isolated_cli_runner.invoke(
        agent_cli,
        ["add", "--name", "Test Agent", "--description", "A helper", "--type", "general"],
    )
    assert added.exit_code == 0
    assert "Test Agent" in added.output

    duplicate = isolated_cli_runner.invoke(
        agent_cli,
        ["add", "--name", "Test Agent", "--description", "A helper", "--type", "general"],
    )
    assert duplicate.exit_code == 0
    assert "already exists" in duplicate.output

    listed = isolated_cli_runner.invoke(agent_cli, ["list"])
    assert "test_agent: Test Agent (inactive) - A helper" in listed.output

    updated = isolated_cli_runner.invoke(
        agent_cli,
        ["update", "test_agent", "--name", "Updated", "--type", "specialized"],
    )
    assert updated.exit_code == 0
    assert "updated successfully" in updated.output

    goal = isolated_cli_runner.invoke(
        agent_cli, ["set-goal", "test_agent", "--goal", "Add 2 and 5"]
    )
    assert goal.exit_code == 0
    assert "Goal set" in goal.output
    assert load_agents()["test_agent"]["goal"] == "Add 2 and 5"

    removed = isolated_cli_runner.invoke(agent_cli, ["remove", "test_agent", "--yes"])
    assert removed.exit_code == 0
    assert "removed successfully" in removed.output


def test_agent_missing_paths_and_invalid_tool_arguments(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    for command in (
        ["update", "missing", "--name", "x"],
        ["remove", "missing", "--yes"],
        ["set-goal", "missing", "--goal", "x"],
        ["ask", "missing", "--prompt", "hello"],
        ["tool-list", "missing"],
    ):
        result = isolated_cli_runner.invoke(agent_cli, command)
        assert result.exit_code == 0
        assert "not found" in result.output

    invalid_json = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", "nope"]
    )
    assert invalid_json.exit_code == 0
    assert "Invalid JSON" in invalid_json.output

    not_object = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", "[1, 2]"]
    )
    assert not_object.exit_code == 0
    assert "--arguments must be a JSON object" in not_object.output


def test_agent_tool_commands_and_deterministic_prompt_fallbacks(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents(
        {
            "agent1": {
                "name": "Agent",
                "description": "desc",
                "goal": "Please add 10 and 5",
            }
        }
    )

    tool_list = isolated_cli_runner.invoke(agent_cli, ["tool-list", "agent1"])
    assert tool_list.exit_code == 0
    assert "cli_echo" in tool_list.output
    assert "cli_add" in tool_list.output
    assert "cli_now_utc" in tool_list.output

    tool_info = isolated_cli_runner.invoke(agent_cli, ["tool-info", "agent1", "cli_add"])
    assert tool_info.exit_code == 0
    assert "Tool: cli_add" in tool_info.output
    assert "Add two integers" in tool_info.output

    missing_tool = isolated_cli_runner.invoke(agent_cli, ["tool-info", "agent1", "missing"])
    assert missing_tool.exit_code == 0
    assert "Tool 'missing' not found" in missing_tool.output

    tool_search = isolated_cli_runner.invoke(agent_cli, ["tool-search", "agent1", "echo"])
    assert tool_search.exit_code == 0
    assert "cli_echo" in tool_search.output

    no_match = isolated_cli_runner.invoke(agent_cli, ["tool-search", "agent1", "zzzz"])
    assert no_match.exit_code == 0
    assert "No tools matched" in no_match.output

    tool_run = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", '{"a": 4, "b": 6}']
    )
    assert tool_run.exit_code == 0
    assert "Status: success" in tool_run.output
    assert "Result: 10" in tool_run.output

    asked = isolated_cli_runner.invoke(
        agent_cli, ["ask", "agent1", "--prompt", "echo hello there"]
    )
    assert asked.exit_code == 0
    assert "Agent response: Used tool cli_echo -> hello there" in asked.output

    run = isolated_cli_runner.invoke(agent_cli, ["run", "agent1"])
    assert run.exit_code == 0
    assert "Agent response: Used tool cli_add -> 15" in run.output
    assert load_agents()["agent1"]["status"] == "running"

    async_run = isolated_cli_runner.invoke(agent_cli, ["run", "agent1", "--async"])
    assert async_run.exit_code == 0
    assert "started asynchronously" in async_run.output


def test_agent_run_without_goal_and_async_model_fallback(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc", "goal": None}})

    no_goal = isolated_cli_runner.invoke(agent_cli, ["run", "agent1"])
    assert no_goal.exit_code == 0
    assert "has no goal set" in no_goal.output

    class RuntimeAgent:
        async def run(self, prompt):
            return f"model says {prompt}"

        def execute(self, *args, **kwargs):
            raise AssertionError("tool fallback should not run")

    assert _execute_prompt_with_tool_fallback(RuntimeAgent(), "tell me a joke") == (
        "model says tell me a joke"
    )


def test_agent_prompt_fallback_reports_tool_errors():
    class FailedToolAgent:
        def execute(self, *args, **kwargs):
            return SimpleNamespace(error="bad input", result=None)

    assert (
        _execute_prompt_with_tool_fallback(FailedToolAgent(), "add 1 and 2")
        == "Tool error: bad input"
    )
