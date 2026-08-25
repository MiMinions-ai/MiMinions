"""
Unit tests for the MiMinions CLI execution module.
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from miminions.cli.main import cli
from miminions.workflow.models import AgentRunRecord, WorkflowRun, ToolCallRecord, WorkflowTrace


# ── Fixtures ─────────────────────────────────────────────────────────────────

@pytest.fixture
def runner():
    return CliRunner()


@pytest.fixture
def config_dir(tmp_path):
    config = tmp_path / ".miminions"
    config.mkdir()
    return config


@pytest.fixture
def authenticated(config_dir):
    """Pre-authenticated config dir so auth checks pass."""
    auth_file = config_dir / "auth.json"
    auth_file.write_text(json.dumps({"username": "testuser", "authenticated": True}))
    return config_dir


@pytest.fixture
def active_session(config_dir):
    """Config dir with one active session already in sessions.json."""
    session_id = "abc12345"
    sessions_file = config_dir / "sessions.json"
    sessions_file.write_text(json.dumps({
        session_id: {
            "name": "test-session",
            "status": "active",
            "started_at": "2026-01-01T00:00:00",
            "interaction_count": 0,
            "tool_sources": [],
        }
    }))
    return config_dir, session_id


@pytest.fixture
def mock_agent():
    """MagicMock standing in for a fully constructed Agent."""
    agent = MagicMock()
    agent.list_tools.return_value = ["calculator"]
    agent.get_tool.return_value = MagicMock()
    agent.execute_tool.return_value = "42"

    async def mock_execute_async(tool_name, *args, **kwargs):
        if tool_name not in agent.list_tools():
            raise ValueError(f"Tool {tool_name} not found")
        return "42"
    agent.execute_tool_async = mock_execute_async
    return agent


def _make_workflow_run_dict(session_id: str, tool_name: str = "calculator", status: str = "success") -> dict:
    """Helper: build a WorkflowRun dict in the format interactions.json now uses."""
    trace = WorkflowTrace()
    agent_rec = AgentRunRecord(prompt=f"Execute tool: {tool_name}", output="42")
    trace.add_agent_record(agent_rec)
    trace.add_tool_record(
        tool_name=tool_name,
        kwargs={"a": 1},
        result="42",
        error=None,
        status=status,
        execution_time_ms=10.0,
    )
    wf = WorkflowRun(agent_name=f"session-{session_id}", trace=trace)
    return wf.to_dict()


# ── Help / smoke ──────────────────────────────────────────────────────────────

class TestExecutionHelp:

    def test_execution_help(self, runner):
        result = runner.invoke(cli, ["execution", "--help"])
        assert result.exit_code == 0, f"expect cli execution --help to exit with 0, got {result.exit_code} with output: {result.output}"
        assert "session" in result.output, f"expect the result to contain 'session', got {result.output}"
        assert "interaction" in result.output, f"expect the result to contain 'interaction', got {result.output}"
        assert "test" in result.output, f"expect the result to contain 'test', got {result.output}"

    def test_session_help(self, runner):
        result = runner.invoke(cli, ["execution", "session", "--help"])
        assert result.exit_code == 0, f"expect cli execution session --help to exit with 0, got {result.exit_code} with output: {result.output}"
        assert "start" in result.output, f"expect the result to contain 'start', got {result.output}"
        assert "stop" in result.output, f"expect the result to contain 'stop', got {result.output}"
        assert "list" in result.output, f"expect the result to contain 'list', got {result.output}"

    def test_interactions_help(self, runner):
        result = runner.invoke(cli, ["execution", "interaction", "--help"])
        assert result.exit_code == 0, f"expect cli execution interaction --help to exit with 0, got {result.exit_code} with output: {result.output}"
        assert "list" in result.output, f"expect the result to contain 'list', got {result.output}"
        assert "show" in result.output, f"expect the result to contain 'show', got {result.output}"


# ── Session management ────────────────────────────────────────────────────────

class TestSessionManagement:

    def test_start_session(self, runner, authenticated):
        with patch("miminions.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "session", "start", "--name", "my-session"])
            assert result.exit_code == 0, f"expect cli execution session start --name my-session to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "Session started" in result.output, f"expect the result to contain 'Session started', got {result.output}"

    def test_start_session_blocks_duplicate(self, runner, authenticated, active_session):
        config_dir, _ = active_session
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "session", "start", "--name", "new-session"])
            assert result.exit_code == 0, f"expect cli execution session start --name new-session to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "already active" in result.output, f"expect the result to contain 'already active', got {result.output}"

    def test_list_sessions_empty(self, runner, authenticated):
        with patch("miminions.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "session", "list"])
            assert result.exit_code == 0, f"expect cli execution session list to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "No sessions found" in result.output, f"expect the result to contain 'No sessions found', got {result.output}"

    def test_list_sessions_shows_active(self, runner, authenticated, active_session):
        config_dir, session_id = active_session
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "session", "list"])
            assert result.exit_code == 0, f"expect cli execution session list to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "test-session" in result.output, f"expect the result to contain 'test-session', got {result.output}"
            assert "active" in result.output, f"expect the result to contain 'active', got {result.output}"

    def test_stop_active_session(self, runner, authenticated, active_session):
        config_dir, _ = active_session
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "session", "stop"])
            assert result.exit_code == 0, f"expect cli execution session stop to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "stopped" in result.output, f"expect the result to contain 'stopped', got {result.output}"

    def test_stop_no_active_session(self, runner, authenticated):
        with patch("miminions.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "session", "stop"])
            assert result.exit_code == 0, f"expect cli execution session stop to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "No active session" in result.output, f"expect the result to contain 'No active session', got {result.output}"


# ── Tool execution ────────────────────────────────────────────────────────────

class TestToolExecution:

    def test_run_no_active_session(self, runner, authenticated):
        with patch("miminions.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "run", "calculator"])
            assert result.exit_code == 0, f"expect cli execution run calculator to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "No active session" in result.output, f"expect the result to contain 'No active session', got {result.output}"

    def test_run_tool_not_found(self, runner, authenticated, active_session, mock_agent):
        config_dir, _ = active_session
        mock_agent.get_tool.return_value = None
        mock_agent.list_tools.return_value = []
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution._build_agent", return_value=mock_agent):
            result = runner.invoke(cli, ["execution", "run", "nonexistent_tool"])
            assert result.exit_code == 0, f"expect cli execution run nonexistent_tool to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "not found" in result.output, f"expect the result to contain 'not found', got {result.output}"

    def test_run_tool_success(self, runner, authenticated, active_session, mock_agent):
        config_dir, _ = active_session
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution._build_agent", return_value=mock_agent):
            result = runner.invoke(cli, ["execution", "run", "calculator", "--input", "a=1"])
            assert result.exit_code == 0, f"expect cli execution run calculator to exit with 0, got {result.exit_code} with output: {result.output}"
            assert "42" in result.output, f"expect contains '42', got {result.output}"

    def test_run_tool_logs_interaction_as_workflow_run(self, runner, authenticated, active_session, mock_agent):
        """Interactions are now persisted as WorkflowRun objects, not raw dicts."""
        config_dir, session_id = active_session
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution._build_agent", return_value=mock_agent):
            runner.invoke(cli, ["execution", "run", "calculator", "--input", "a=1"])
            interactions_file = config_dir / "interactions.json"
            file_exists = interactions_file.exists()
            assert file_exists, f"expect interactions.json should be created after a run, got {file_exists}"
            raw = json.loads(interactions_file.read_text())
            assert session_id in raw, f"expect the created interactions file to contain session_id, got {raw}"
            runs = raw[session_id]
            no_runs = len(runs)
            assert no_runs == 1, f"expect the number of runs to be 1, got {no_runs}"
            wf = WorkflowRun.from_dict(runs[0])
            tool_calls = [r for r in wf.trace.records if isinstance(r, ToolCallRecord)]
            no_tool_calls = len(tool_calls)
            assert no_tool_calls == 1, f"expect the number of tool calls to be 1, got {no_tool_calls}"
            assert tool_calls[0].tool_name == "calculator", f"expect the first tool call has name 'calculator', got {tool_calls[0].tool_name}"
            assert tool_calls[0].status == "success", f"expect the first tool call has status 'success', got {tool_calls[0].status}"


# ── Interactions ──────────────────────────────────────────────────────────────

class TestInteractions:

    def test_list_interactions_empty(self, runner, authenticated, active_session):
        config_dir, _ = active_session
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "interaction", "list"])
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"

    def test_show_interaction_index_out_of_range(self, runner, authenticated, active_session):
        """show takes an integer index — passing 99 on an empty log returns not found."""
        config_dir, _ = active_session
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "interaction", "show", "99"])
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert "No interaction at index" in result.output, f"expect contains 'No interaction at index', got {result.output}"

    def test_show_interaction_found(self, runner, authenticated, active_session):
        """interactions.json now stores WorkflowRun dicts keyed by session_id."""
        config_dir, session_id = active_session
        wf_dict = _make_workflow_run_dict(session_id, tool_name="calculator", status="success")
        interactions_file = config_dir / "interactions.json"
        interactions_file.write_text(json.dumps({session_id: [wf_dict]}))
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "interaction", "show", "0",
                                         "--session-id", session_id])
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert "calculator" in result.output, f"expect contains 'calculator', got {result.output}"
            assert "success" in result.output, f"expect contains 'success', got {result.output}"


# ── Auth guard ────────────────────────────────────────────────────────────────

class TestAuthGuard:

    def test_session_start_requires_auth(self, runner, config_dir):
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "session", "start"])
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            output_lower = result.output.lower()
            target_value = "sign in"
            assert target_value in output_lower, f"expect {target_value} in lowercased result output, got {output_lower}"

    def test_run_requires_auth(self, runner, config_dir):
        with patch("miminions.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "run", "some_tool"])
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            output_lower = result.output.lower()
            target_value = "sign in"
            assert target_value in output_lower, f"expect {target_value} in lowercased result output, got {output_lower}"
