import json
from types import SimpleNamespace

from miminions.cli.agent import (
    _execute_prompt_with_tool_fallback,
    _extract_first_two_ints,
    agent_cli,
    load_agents,
    save_agents,
)


NONEXISTENT_AGENT_ID = "agent-does-not-exist"
NONEXISTENT_TOOL_NAME = "tool-does-not-exist"


def _assert_exit_code(result, expected: int, behavior: str) -> None:
    assert result.exit_code == expected, (
        f"Expected {behavior} to exit with {expected} and got "
        f"{result.exit_code}. Output: {result.output}"
    )


def test_agent_storage_helpers_and_integer_extraction(tmp_path, monkeypatch):
    """Agent persistence helpers should round-trip JSON and parse signed integers."""
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)

    assert load_agents() == {}, f"Expected no stored agents and got {load_agents()}."
    save_agents({"agent1": {"name": "Agent One"}})
    assert load_agents() == {"agent1": {"name": "Agent One"}}, (
        f"Expected saved agent record and got {load_agents()}."
    )

    parsed_pair = _extract_first_two_ints("add -3 and 14 please")
    assert parsed_pair == (-3, 14), (
        f"Expected first two integers (-3, 14) and got {parsed_pair}."
    )
    parsed_single = _extract_first_two_ints("only one 7")
    assert parsed_single is None, (
        f"Expected no integer pair for single-number prompt and got {parsed_single}."
    )


def test_agent_add_list_update_goal_remove(isolated_cli_runner, tmp_path, monkeypatch):
    """Agent CRUD commands should persist the expected CLI agent record changes."""
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)

    added = isolated_cli_runner.invoke(
        agent_cli,
        ["add", "--name", "Test Agent", "--description", "A helper", "--type", "general"],
    )
    _assert_exit_code(added, 0, "adding an agent")
    assert "Test Agent" in added.output, (
        f"Expected added agent name in output and got: {added.output}"
    )

    duplicate = isolated_cli_runner.invoke(
        agent_cli,
        ["add", "--name", "Test Agent", "--description", "A helper", "--type", "general"],
    )
    _assert_exit_code(duplicate, 0, "adding a duplicate agent")
    assert "already exists" in duplicate.output, (
        f"Expected duplicate-agent warning and got: {duplicate.output}"
    )

    listed = isolated_cli_runner.invoke(agent_cli, ["list"])
    assert "test_agent: Test Agent (inactive) - A helper" in listed.output, (
        f"Expected persisted agent details in list output and got: {listed.output}"
    )

    updated = isolated_cli_runner.invoke(
        agent_cli,
        ["update", "test_agent", "--name", "Updated", "--type", "specialized"],
    )
    _assert_exit_code(updated, 0, "updating an agent")
    assert "updated successfully" in updated.output, (
        f"Expected update success message and got: {updated.output}"
    )

    goal = isolated_cli_runner.invoke(
        agent_cli, ["set-goal", "test_agent", "--goal", "Add 2 and 5"]
    )
    _assert_exit_code(goal, 0, "setting an agent goal")
    assert "Goal set" in goal.output, f"Expected goal-set message and got: {goal.output}"
    stored_goal = load_agents()["test_agent"]["goal"]
    assert stored_goal == "Add 2 and 5", (
        f"Expected stored goal 'Add 2 and 5' and got {stored_goal!r}."
    )

    removed = isolated_cli_runner.invoke(agent_cli, ["remove", "test_agent", "--yes"])
    _assert_exit_code(removed, 0, "removing an agent")
    assert "removed successfully" in removed.output, (
        f"Expected remove success message and got: {removed.output}"
    )


def test_agent_update_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(
        agent_cli, ["update", NONEXISTENT_AGENT_ID, "--name", "x"]
    )

    _assert_exit_code(result, 0, "updating a nonexistent agent")
    assert f"Agent '{NONEXISTENT_AGENT_ID}' not found." in result.output, (
        f"Expected nonexistent-agent update error and got: {result.output}"
    )


def test_agent_remove_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(
        agent_cli, ["remove", NONEXISTENT_AGENT_ID, "--yes"]
    )

    _assert_exit_code(result, 0, "removing a nonexistent agent")
    assert f"Agent '{NONEXISTENT_AGENT_ID}' not found." in result.output, (
        f"Expected nonexistent-agent remove error and got: {result.output}"
    )


def test_agent_set_goal_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(
        agent_cli, ["set-goal", NONEXISTENT_AGENT_ID, "--goal", "x"]
    )

    _assert_exit_code(result, 0, "setting a goal for a nonexistent agent")
    assert f"Agent '{NONEXISTENT_AGENT_ID}' not found." in result.output, (
        f"Expected nonexistent-agent set-goal error and got: {result.output}"
    )


def test_agent_ask_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(
        agent_cli, ["ask", NONEXISTENT_AGENT_ID, "--prompt", "hello"]
    )

    _assert_exit_code(result, 0, "asking a nonexistent agent")
    assert f"Agent '{NONEXISTENT_AGENT_ID}' not found." in result.output, (
        f"Expected nonexistent-agent ask error and got: {result.output}"
    )


def test_agent_tool_list_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(agent_cli, ["tool-list", NONEXISTENT_AGENT_ID])

    _assert_exit_code(result, 0, "listing tools for a nonexistent agent")
    assert f"Agent '{NONEXISTENT_AGENT_ID}' not found." in result.output, (
        f"Expected nonexistent-agent tool-list error and got: {result.output}"
    )


def test_agent_tool_run_rejects_invalid_json_arguments(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    invalid_json = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", "nope"]
    )
    _assert_exit_code(invalid_json, 0, "running a tool with invalid JSON arguments")
    assert "Invalid JSON" in invalid_json.output, (
        f"Expected invalid JSON error and got: {invalid_json.output}"
    )


def test_agent_tool_run_rejects_non_object_json_arguments(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    not_object = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", "[1, 2]"]
    )
    _assert_exit_code(not_object, 0, "running a tool with non-object JSON arguments")
    assert "--arguments must be a JSON object" in not_object.output, (
        f"Expected JSON object error and got: {not_object.output}"
    )


def test_agent_tool_commands_and_deterministic_prompt_fallbacks(
    isolated_cli_runner, tmp_path, monkeypatch
):
    """Tool commands should expose runtime tools and deterministic prompt routing."""
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
    _assert_exit_code(tool_list, 0, "listing agent tools")
    assert "cli_echo" in tool_list.output, f"Expected cli_echo and got: {tool_list.output}"
    assert "cli_add" in tool_list.output, f"Expected cli_add and got: {tool_list.output}"
    assert "cli_now_utc" in tool_list.output, (
        f"Expected cli_now_utc and got: {tool_list.output}"
    )

    tool_info = isolated_cli_runner.invoke(agent_cli, ["tool-info", "agent1", "cli_add"])
    _assert_exit_code(tool_info, 0, "showing tool info")
    assert "Tool: cli_add" in tool_info.output, (
        f"Expected cli_add tool info and got: {tool_info.output}"
    )
    assert "Add two integers" in tool_info.output, (
        f"Expected cli_add description and got: {tool_info.output}"
    )

    missing_tool = isolated_cli_runner.invoke(
        agent_cli, ["tool-info", "agent1", NONEXISTENT_TOOL_NAME]
    )
    assert missing_tool.exit_code == 0
    assert f"Tool '{NONEXISTENT_TOOL_NAME}' not found" in missing_tool.output, (
        f"Expected nonexistent-tool info error and got: {missing_tool.output}"
    )

    tool_search = isolated_cli_runner.invoke(agent_cli, ["tool-search", "agent1", "echo"])
    _assert_exit_code(tool_search, 0, "searching agent tools")
    assert "cli_echo" in tool_search.output, (
        f"Expected cli_echo search result and got: {tool_search.output}"
    )

    no_match = isolated_cli_runner.invoke(agent_cli, ["tool-search", "agent1", "zzzz"])
    _assert_exit_code(no_match, 0, "searching for unmatched agent tools")
    assert "No tools matched" in no_match.output, (
        f"Expected no tool match message and got: {no_match.output}"
    )

    tool_run = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", '{"a": 4, "b": 6}']
    )
    _assert_exit_code(tool_run, 0, "running cli_add")
    assert "Status: success" in tool_run.output, (
        f"Expected successful tool status and got: {tool_run.output}"
    )
    assert "Result: 10" in tool_run.output, (
        f"Expected cli_add result 10 and got: {tool_run.output}"
    )

    asked = isolated_cli_runner.invoke(
        agent_cli, ["ask", "agent1", "--prompt", "echo hello there"]
    )
    _assert_exit_code(asked, 0, "asking agent with echo prompt")
    assert "Agent response: Used tool cli_echo -> hello there" in asked.output, (
        f"Expected deterministic echo response and got: {asked.output}"
    )

    run = isolated_cli_runner.invoke(agent_cli, ["run", "agent1"])
    _assert_exit_code(run, 0, "running agent with arithmetic goal")
    assert "Agent response: Used tool cli_add -> 15" in run.output, (
        f"Expected deterministic addition response and got: {run.output}"
    )
    stored_status = load_agents()["agent1"]["status"]
    assert stored_status == "running", (
        f"Expected stored agent status 'running' and got {stored_status!r}."
    )

    async_run = isolated_cli_runner.invoke(agent_cli, ["run", "agent1", "--async"])
    _assert_exit_code(async_run, 0, "starting agent async run")
    assert "started asynchronously" in async_run.output, (
        f"Expected async start message and got: {async_run.output}"
    )


def test_agent_run_reports_missing_goal(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc", "goal": None}})

    no_goal = isolated_cli_runner.invoke(agent_cli, ["run", "agent1"])
    _assert_exit_code(no_goal, 0, "running an agent without a goal")
    assert "has no goal set" in no_goal.output, (
        f"Expected missing-goal message and got: {no_goal.output}"
    )


def test_prompt_execution_delegates_to_model_when_no_deterministic_tool_matches():
    """Prompts that do not match CLI tool routing should be sent to the runtime model."""
    class RuntimeAgent:
        async def run(self, prompt):
            return f"model says {prompt}"

        def execute(self, *args, **kwargs):
            raise AssertionError("tool fallback should not run")

    output = _execute_prompt_with_tool_fallback(RuntimeAgent(), "tell me a joke")
    assert output == "model says tell me a joke", (
        f"Expected model response for unrouted prompt and got {output!r}."
    )


def test_agent_prompt_fallback_reports_tool_errors():
    """Deterministic tool routing should return tool execution errors directly."""
    class FailedToolAgent:
        def execute(self, *args, **kwargs):
            return SimpleNamespace(error="bad input", result=None)

    output = _execute_prompt_with_tool_fallback(FailedToolAgent(), "add 1 and 2")
    assert output == "Tool error: bad input", (
        f"Expected tool error message and got {output!r}."
    )
