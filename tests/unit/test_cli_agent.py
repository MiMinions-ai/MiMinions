from miminions.cli.agent import (
    agent_cli,
    load_agents,
    save_agents,
)

NONEXISTENT_AGENT_ID = "agent-does-not-exist"


def _assert_exit_code(result, expected: int, behavior: str) -> None:
    assert result.exit_code == expected, f"expect cli exit code {expected}, got {result.exit_code} with output: {result.output}"


def test_agent_storage_helpers(tmp_path, monkeypatch):
    """Agent persistence helpers should round-trip JSON."""
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)

    initial_agents = load_agents()
    target_value = {}
    assert initial_agents == target_value, f"expect result to be {target_value}, got {initial_agents}"
    save_agents({"agent1": {"name": "Agent One"}})
    loaded_agents = load_agents()
    target_value = {"agent1": {"name": "Agent One"}}
    assert loaded_agents == target_value, f"expect result to be {target_value}, got {loaded_agents}"


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


def test_agent_commands_and_runtime_prompt_execution(
    isolated_cli_runner, tmp_path, monkeypatch
):
    """Agent prompts should go through the runtime without making network requests."""
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)

    async def mock_runtime(_agent_data, _operation, **params):
        return f"model says {params['prompt']}"

    monkeypatch.setattr(
        "miminions.cli.agent._run_with_agent_runtime", mock_runtime
    )
    save_agents(
        {
            "agent1": {
                "name": "Agent",
                "description": "desc",
                "goal": "Please add 10 and 5",
            }
        }
    )

    asked = isolated_cli_runner.invoke(
        agent_cli, ["ask", "agent1", "--prompt", "echo hello there"]
    )
    _assert_exit_code(asked, 0, "asking agent with echo prompt")
    assert "Agent response: model says echo hello there" in asked.output, f"expect 'Agent response: model says echo hello there' in asked.output, got {asked.output}"

    run = isolated_cli_runner.invoke(agent_cli, ["run", "agent1"])
    _assert_exit_code(run, 0, "running agent through runtime")
    assert "Agent response: model says Please add 10 and 5" in run.output, f"expect 'Agent response: model says Please add 10 and 5' in run.output, got {run.output}"
    stored_status = load_agents()["agent1"]["status"]
    assert stored_status == "running", f"expect result to be {'running'}, got {stored_status}"

    async_run = isolated_cli_runner.invoke(agent_cli, ["run", "agent1", "--async"])
    _assert_exit_code(async_run, 2, "rejecting removed async run flag")
    assert "No such option" in async_run.output, f"expect 'No such option' in async_run.output, got {async_run.output}"
    assert "--async" in async_run.output, f"expect '--async' in async_run.output, got {async_run.output}"


def test_agent_run_reports_missing_goal(
    isolated_cli_runner, tmp_path, monkeypatch
):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc", "goal": None}})

    no_goal = isolated_cli_runner.invoke(agent_cli, ["run", "agent1"])
    _assert_exit_code(no_goal, 0, "running an agent without a goal")
    assert "has no goal set" in no_goal.output, f"expect 'has no goal set' in no_goal.output, got {no_goal.output}"
