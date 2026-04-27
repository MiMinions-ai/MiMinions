"""
Unit tests for the MiMinions CLI execution module.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from miminions.interface.cli.main import cli
from miminions.workflow.models import AgentRunRecord, WorkflowRun


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
    return agent


def _make_workflow_run_dict(session_id: str, tool_name: str = "calculator", status: str = "success") -> dict:
    """Helper: build a WorkflowRun dict in the format interactions.json now uses."""
    run = AgentRunRecord(prompt=f"Execute tool: {tool_name}")
    run.record_tool_call(
        tool_name=tool_name,
        kwargs={"a": 1},
        result="42",
        error=None,
        status=status,
        execution_time_ms=10.0,
    )
    run.output = "42"
    wf = WorkflowRun(agent_name=f"session-{session_id}", run=run)
    return wf.to_dict()


# ── Help / smoke ──────────────────────────────────────────────────────────────

class TestExecutionHelp:

    def test_execution_help(self, runner):
        result = runner.invoke(cli, ["execution", "--help"])
        assert result.exit_code == 0
        assert "session" in result.output
        assert "interaction" in result.output
        assert "test" in result.output

    def test_session_help(self, runner):
        result = runner.invoke(cli, ["execution", "session", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "stop" in result.output
        assert "list" in result.output

    def test_interactions_help(self, runner):
        result = runner.invoke(cli, ["execution", "interaction", "--help"])
        assert result.exit_code == 0
        assert "list" in result.output
        assert "show" in result.output


# ── Session management ────────────────────────────────────────────────────────

class TestSessionManagement:

    def test_start_session(self, runner, authenticated):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "session", "start", "--name", "my-session"])
            assert result.exit_code == 0
            assert "Session started" in result.output

    def test_start_session_blocks_duplicate(self, runner, authenticated, active_session):
        config_dir, _ = active_session
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "session", "start", "--name", "new-session"])
            assert result.exit_code == 0
            assert "already active" in result.output

    def test_list_sessions_empty(self, runner, authenticated):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "session", "list"])
            assert result.exit_code == 0
            assert "No sessions found" in result.output

    def test_list_sessions_shows_active(self, runner, authenticated, active_session):
        config_dir, session_id = active_session
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "session", "list"])
            assert result.exit_code == 0
            assert "test-session" in result.output
            assert "active" in result.output

    def test_stop_active_session(self, runner, authenticated, active_session):
        config_dir, _ = active_session
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "session", "stop"])
            assert result.exit_code == 0
            assert "stopped" in result.output

    def test_stop_no_active_session(self, runner, authenticated):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "session", "stop"])
            assert result.exit_code == 0
            assert "No active session" in result.output


# ── Tool execution ────────────────────────────────────────────────────────────

class TestToolExecution:

    def test_run_no_active_session(self, runner, authenticated):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "run", "calculator"])
            assert result.exit_code == 0
            assert "No active session" in result.output

    def test_run_tool_not_found(self, runner, authenticated, active_session, mock_agent):
        config_dir, _ = active_session
        mock_agent.get_tool.return_value = None
        mock_agent.list_tools.return_value = []
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution._build_agent", return_value=mock_agent):
            result = runner.invoke(cli, ["execution", "run", "nonexistent_tool"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_run_tool_success(self, runner, authenticated, active_session, mock_agent):
        config_dir, _ = active_session
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution._build_agent", return_value=mock_agent):
            result = runner.invoke(cli, ["execution", "run", "calculator", "--input", "a=1"])
            assert result.exit_code == 0
            assert "42" in result.output

    def test_run_tool_logs_interaction_as_workflow_run(self, runner, authenticated, active_session, mock_agent):
        """Interactions are now persisted as WorkflowRun objects, not raw dicts."""
        config_dir, session_id = active_session
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution._build_agent", return_value=mock_agent):
            runner.invoke(cli, ["execution", "run", "calculator", "--input", "a=1"])
            interactions_file = config_dir / "interactions.json"
            assert interactions_file.exists(), "interactions.json should be created after a run"
            raw = json.loads(interactions_file.read_text())
            assert session_id in raw, f"Expected session_id '{session_id}' as a key in interactions.json"
            runs = raw[session_id]
            assert len(runs) == 1, f"Expected 1 recorded WorkflowRun, got {len(runs)}"
            wf = WorkflowRun.from_dict(runs[0])
            assert len(wf.run.tool_calls) == 1, f"Expected 1 tool call, got {len(wf.run.tool_calls)}"
            assert wf.run.tool_calls[0].tool_name == "calculator", \
                f"Expected tool_name 'calculator', got '{wf.run.tool_calls[0].tool_name}'"
            assert wf.run.tool_calls[0].status == "success", \
                f"Expected status 'success', got '{wf.run.tool_calls[0].status}'"


# ── Interactions ──────────────────────────────────────────────────────────────

class TestInteractions:

    def test_list_interactions_empty(self, runner, authenticated):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "interaction", "list"])
            assert result.exit_code == 0

    def test_show_interaction_index_out_of_range(self, runner, authenticated):
        """show takes an integer index — passing 99 on an empty log returns not found."""
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "interaction", "show", "99"])
            assert result.exit_code == 0
            assert "No interaction at index" in result.output

    def test_show_interaction_found(self, runner, authenticated, active_session):
        """interactions.json now stores WorkflowRun dicts keyed by session_id."""
        config_dir, session_id = active_session
        wf_dict = _make_workflow_run_dict(session_id, tool_name="calculator", status="success")
        interactions_file = config_dir / "interactions.json"
        interactions_file.write_text(json.dumps({session_id: [wf_dict]}))
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "interaction", "show", "0",
                                         "--session-id", session_id])
            assert result.exit_code == 0, f"Unexpected output: {result.output}"
            assert "calculator" in result.output, \
                f"Expected 'calculator' in output, got: {result.output}"
            assert "success" in result.output, \
                f"Expected 'success' in output, got: {result.output}"


# ── Auth guard ────────────────────────────────────────────────────────────────

class TestAuthGuard:

    def test_session_start_requires_auth(self, runner, config_dir):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "session", "start"])
            assert result.exit_code == 0
            assert "sign in" in result.output.lower()

    def test_run_requires_auth(self, runner, config_dir):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir):
            result = runner.invoke(cli, ["execution", "run", "some_tool"])
            assert result.exit_code == 0
            assert "sign in" in result.output.lower()
