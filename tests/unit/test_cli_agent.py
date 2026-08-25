import asyncio
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
    assert result.exit_code == expected, f"expect cli exit code {expected}, got {result.exit_code} with output: {result.output}"


def test_agent_storage_helpers_and_integer_extraction(tmp_path, monkeypatch):
    """Agent persistence helpers should round-trip JSON and parse signed integers."""
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)

    initial_agents = load_agents()
    target_value = {}
    assert initial_agents == target_value, f"expect result to be {target_value}, got {initial_agents}"
    save_agents({"agent1": {"name": "Agent One"}})
    loaded_agents = load_agents()
    target_value = {"agent1": {"name": "Agent One"}}
    assert loaded_agents == target_value, f"expect result to be {target_value}, got {loaded_agents}"

    parsed_pair = _extract_first_two_ints("add -3 and 14 please")
    assert parsed_pair == (-3, 14), f"expect result to be {(-3, 14)}, got {parsed_pair}"
    parsed_single = _extract_first_two_ints("only one 7")
    assert parsed_single is None, f"expect result to be {None}, got {parsed_single}"


def test_agent_add_list_update_goal_remove(isolated_cli_runner, tmp_path, monkeypatch):
    """Agent CRUD commands should persist the expected CLI agent record changes."""
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)

    added = isolated_cli_runner.invoke(
        agent_cli,
        ["add", "--name", "Test Agent", "--description", "A helper", "--type", "general"],
    )
    _assert_exit_code(added, 0, "adding an agent")
    assert "Test Agent" in added.output, f"expect 'Test Agent' in added.output, got {added.output}"

    listed = isolated_cli_runner.invoke(agent_cli, ["list"])
    assert "test_agent: Test Agent (inactive) - A helper" in listed.output, f"expect 'test_agent: Test Agent (inactive) - A helper' in listed.output, got {listed.output}"

    updated = isolated_cli_runner.invoke(
        agent_cli,
        ["update", "test_agent", "--name", "Updated", "--type", "specialized"],
    )
    _assert_exit_code(updated, 0, "updating an agent")
    assert "updated successfully" in updated.output, f"expect 'updated successfully' in updated.output, got {updated.output}"

    goal = isolated_cli_runner.invoke(
        agent_cli, ["set-goal", "test_agent", "--goal", "Add 2 and 5"]
    )
    _assert_exit_code(goal, 0, "setting an agent goal")
    assert "Goal set" in goal.output, f"expect 'Goal set' in goal.output, got {goal.output}"
    stored_goal = load_agents()["test_agent"]["goal"]
    assert stored_goal == "Add 2 and 5", f"expect result to be {'Add 2 and 5'}, got {stored_goal}"

    removed = isolated_cli_runner.invoke(agent_cli, ["remove", "test_agent", "--yes"])
    _assert_exit_code(removed, 0, "removing an agent")
    assert "removed successfully" in removed.output, f"expect 'removed successfully' in removed.output, got {removed.output}"


def test_agent_update_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(
        agent_cli, ["update", NONEXISTENT_AGENT_ID, "--name", "x"]
    )

    _assert_exit_code(result, 0, "updating a nonexistent agent")
    target_value = f"Agent '{NONEXISTENT_AGENT_ID}' not found."
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"


def test_agent_remove_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(
        agent_cli, ["remove", NONEXISTENT_AGENT_ID, "--yes"]
    )

    _assert_exit_code(result, 0, "removing a nonexistent agent")
    target_value = f"Agent '{NONEXISTENT_AGENT_ID}' not found."
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"


def test_agent_set_goal_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(
        agent_cli, ["set-goal", NONEXISTENT_AGENT_ID, "--goal", "x"]
    )

    _assert_exit_code(result, 0, "setting a goal for a nonexistent agent")
    target_value = f"Agent '{NONEXISTENT_AGENT_ID}' not found."
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"


def test_agent_ask_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(
        agent_cli, ["ask", NONEXISTENT_AGENT_ID, "--prompt", "hello"]
    )

    _assert_exit_code(result, 0, "asking a nonexistent agent")
    target_value = f"Agent '{NONEXISTENT_AGENT_ID}' not found."
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"


def test_agent_tool_list_reports_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    result = isolated_cli_runner.invoke(agent_cli, ["tool-list", NONEXISTENT_AGENT_ID])

    _assert_exit_code(result, 0, "listing tools for a nonexistent agent")
    target_value = f"Agent '{NONEXISTENT_AGENT_ID}' not found."
    assert target_value in result.output, f"expect {target_value} in result.output, got {result.output}"


def test_agent_tool_run_rejects_invalid_json_arguments(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    invalid_json = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", "nope"]
    )
    _assert_exit_code(invalid_json, 0, "running a tool with invalid JSON arguments")
    assert "Invalid JSON" in invalid_json.output, f"expect 'Invalid JSON' in invalid_json.output, got {invalid_json.output}"


def test_agent_tool_run_rejects_non_object_json_arguments(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    not_object = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", "[1, 2]"]
    )
    _assert_exit_code(not_object, 0, "running a tool with non-object JSON arguments")
    assert "--arguments must be a JSON object" in not_object.output, f"expect '--arguments must be a JSON object' in not_object.output, got {not_object.output}"


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
    assert "cli_echo" in tool_list.output, f"expect 'cli_echo' in tool_list.output, got {tool_list.output}"
    assert "cli_add" in tool_list.output, f"expect 'cli_add' in tool_list.output, got {tool_list.output}"
    assert "cli_now_utc" in tool_list.output, f"expect 'cli_now_utc' in tool_list.output, got {tool_list.output}"

    tool_info = isolated_cli_runner.invoke(agent_cli, ["tool-info", "agent1", "cli_add"])
    _assert_exit_code(tool_info, 0, "showing tool info")
    assert "Tool: cli_add" in tool_info.output, f"expect 'Tool: cli_add' in tool_info.output, got {tool_info.output}"
    assert "Add two integers" in tool_info.output, f"expect 'Add two integers' in tool_info.output, got {tool_info.output}"

    missing_tool = isolated_cli_runner.invoke(
        agent_cli, ["tool-info", "agent1", NONEXISTENT_TOOL_NAME]
    )
    assert missing_tool.exit_code == 0, f"expect cli exit code 0, got {missing_tool.exit_code} with output: {missing_tool.output}"
    target_value = f"Tool '{NONEXISTENT_TOOL_NAME}' not found"
    assert target_value in missing_tool.output, f"expect {target_value} in missing_tool.output, got {missing_tool.output}"

    tool_search = isolated_cli_runner.invoke(agent_cli, ["tool-search", "agent1", "echo"])
    _assert_exit_code(tool_search, 0, "searching agent tools")
    assert "cli_echo" in tool_search.output, f"expect 'cli_echo' in tool_search.output, got {tool_search.output}"

    no_match = isolated_cli_runner.invoke(agent_cli, ["tool-search", "agent1", "zzzz"])
    _assert_exit_code(no_match, 0, "searching for unmatched agent tools")
    assert "No tools matched" in no_match.output, f"expect 'No tools matched' in no_match.output, got {no_match.output}"

    tool_run = isolated_cli_runner.invoke(
        agent_cli, ["tool-run", "agent1", "cli_add", "--arguments", '{"a": 4, "b": 6}']
    )
    _assert_exit_code(tool_run, 0, "running cli_add")
    assert "Status: success" in tool_run.output, f"expect 'Status: success' in tool_run.output, got {tool_run.output}"
    assert "Result: 10" in tool_run.output, f"expect 'Result: 10' in tool_run.output, got {tool_run.output}"

    asked = isolated_cli_runner.invoke(
        agent_cli, ["ask", "agent1", "--prompt", "echo hello there"]
    )
    _assert_exit_code(asked, 0, "asking agent with echo prompt")
    assert "Agent response: Used tool cli_echo -> hello there" in asked.output, f"expect 'Agent response: Used tool cli_echo -> hello there' in asked.output, got {asked.output}"

    run = isolated_cli_runner.invoke(agent_cli, ["run", "agent1"])
    _assert_exit_code(run, 0, "running agent with arithmetic goal")
    assert "Agent response: Used tool cli_add -> 15" in run.output, f"expect 'Agent response: Used tool cli_add -> 15' in run.output, got {run.output}"
    stored_status = load_agents()["agent1"]["status"]
    assert stored_status == "running", f"expect result to be {'running'}, got {stored_status}"

    async_run = isolated_cli_runner.invoke(agent_cli, ["run", "agent1", "--async"])
    _assert_exit_code(async_run, 0, "starting agent async run")
    assert "started asynchronously" in async_run.output, f"expect 'started asynchronously' in async_run.output, got {async_run.output}"


def test_agent_run_reports_missing_goal(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc", "goal": None}})

    no_goal = isolated_cli_runner.invoke(agent_cli, ["run", "agent1"])
    _assert_exit_code(no_goal, 0, "running an agent without a goal")
    assert "has no goal set" in no_goal.output, f"expect 'has no goal set' in no_goal.output, got {no_goal.output}"


def test_prompt_execution_delegates_to_model_when_no_deterministic_tool_matches():
    """Prompts that do not match CLI tool routing should be sent to the runtime model."""
    class RuntimeAgent:
        async def run(self, prompt):
            return f"model says {prompt}"

        def execute(self, *args, **kwargs):
            raise AssertionError("tool fallback should not run")

    output = asyncio.run(
        _execute_prompt_with_tool_fallback(RuntimeAgent(), "tell me a joke")
    )
    assert output == "model says tell me a joke", f"expect result to be {'model says tell me a joke'}, got {output}"


def test_agent_prompt_fallback_reports_tool_errors():
    """Deterministic tool routing should return tool execution errors directly."""
    class FailedToolAgent:
        def execute(self, *args, **kwargs):
            return SimpleNamespace(error="bad input", result=None)

    output = asyncio.run(
        _execute_prompt_with_tool_fallback(FailedToolAgent(), "add 1 and 2")
    )
    assert output == "Tool error: bad input", f"expect result to be {'Tool error: bad input'}, got {output}"
