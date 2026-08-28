from miminions.cli.agent import save_agents
from miminions.cli.tool import tool_cli

NONEXISTENT_AGENT_ID = "agent-does-not-exist"
NONEXISTENT_TOOL_NAME = "tool-does-not-exist"


def _assert_exit_code(result, expected: int, behavior: str) -> None:
    assert result.exit_code == expected, (
        f"expect cli exit code {expected}, got {result.exit_code} "
        f"while {behavior}, with output: {result.output}"
    )


def test_tool_group_help_and_nonexistent_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    help_result = isolated_cli_runner.invoke(tool_cli, ["--help"])
    _assert_exit_code(help_result, 0, "showing tool group help")
    for command in ("list", "info", "search", "run"):
        assert command in help_result.output

    result = isolated_cli_runner.invoke(tool_cli, ["list", NONEXISTENT_AGENT_ID])
    _assert_exit_code(result, 0, "listing tools for a nonexistent agent")
    assert f"Agent '{NONEXISTENT_AGENT_ID}' not found." in result.output


def test_tool_commands_use_configured_default_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("miminions.cli.config.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})
    (tmp_path / "config.json").write_text(
        '{"default_agent": "agent1"}', encoding="utf-8"
    )

    invocations = (
        (["list"], "cli_add"),
        (["info", "cli_add"], "Tool: cli_add"),
        (["search", "echo"], "cli_echo"),
        (["run", "cli_add", "--arguments", '{"a": 3, "b": 4}'], "Result: 7"),
    )
    for arguments, expected in invocations:
        result = isolated_cli_runner.invoke(tool_cli, arguments)
        _assert_exit_code(
            result, 0, f"running tool command {arguments[0]} with the default agent"
        )
        assert expected in result.output


def test_tool_commands_with_explicit_agent(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    tool_list = isolated_cli_runner.invoke(tool_cli, ["list", "agent1"])
    _assert_exit_code(tool_list, 0, "listing agent tools")
    for name in ("cli_echo", "cli_add", "cli_now_utc"):
        assert name in tool_list.output

    tool_info = isolated_cli_runner.invoke(tool_cli, ["info", "agent1", "cli_add"])
    _assert_exit_code(tool_info, 0, "showing tool info")
    assert "Tool: cli_add" in tool_info.output
    assert "Add two integers" in tool_info.output

    missing_tool = isolated_cli_runner.invoke(
        tool_cli, ["info", "agent1", NONEXISTENT_TOOL_NAME]
    )
    _assert_exit_code(missing_tool, 0, "showing a missing tool")
    assert f"Tool '{NONEXISTENT_TOOL_NAME}' not found" in missing_tool.output

    tool_search = isolated_cli_runner.invoke(tool_cli, ["search", "agent1", "echo"])
    _assert_exit_code(tool_search, 0, "searching agent tools")
    assert "cli_echo" in tool_search.output

    no_match = isolated_cli_runner.invoke(tool_cli, ["search", "agent1", "zzzz"])
    _assert_exit_code(no_match, 0, "searching for unmatched agent tools")
    assert "No tools matched" in no_match.output

    tool_run = isolated_cli_runner.invoke(
        tool_cli, ["run", "agent1", "cli_add", "--arguments", '{"a": 4, "b": 6}']
    )
    _assert_exit_code(tool_run, 0, "running cli_add")
    assert "Status: success" in tool_run.output
    assert "Result: 10" in tool_run.output


def test_tool_run_rejects_invalid_arguments(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.agent.get_config_dir", lambda: tmp_path)
    save_agents({"agent1": {"name": "Agent", "description": "desc"}})

    invalid_json = isolated_cli_runner.invoke(
        tool_cli, ["run", "agent1", "cli_add", "--arguments", "nope"]
    )
    _assert_exit_code(invalid_json, 0, "running a tool with invalid JSON")
    assert "Invalid JSON" in invalid_json.output

    not_object = isolated_cli_runner.invoke(
        tool_cli, ["run", "agent1", "cli_add", "--arguments", "[1, 2]"]
    )
    _assert_exit_code(not_object, 0, "running a tool with non-object arguments")
    assert "--arguments must be a JSON object" in not_object.output
