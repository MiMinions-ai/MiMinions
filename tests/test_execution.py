"""
Unit tests for the MiMinions CLI execution module.
"""

import pytest
import json
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from miminions.interface.cli.main import cli


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


# ── Help / smoke ──────────────────────────────────────────────────────────────

class TestExecutionHelp:

    def test_execution_help(self, runner):
        result = runner.invoke(cli, ["execution", "--help"])
        assert result.exit_code == 0
        assert "session" in result.output
        assert "interactions" in result.output
        assert "test" in result.output

    def test_session_help(self, runner):
        result = runner.invoke(cli, ["execution", "session", "--help"])
        assert result.exit_code == 0
        assert "start" in result.output
        assert "stop" in result.output
        assert "list" in result.output

    def test_interactions_help(self, runner):
        result = runner.invoke(cli, ["execution", "interactions", "--help"])
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
            assert "my-session" in result.output or "ID:" in result.output

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

    def test_run_tool_logs_interaction(self, runner, authenticated, active_session, mock_agent):
        config_dir, session_id = active_session
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=config_dir), \
             patch("miminions.interface.cli.execution._build_agent", return_value=mock_agent):
            runner.invoke(cli, ["execution", "run", "calculator", "--input", "a=1"])
            interactions_file = config_dir / "interactions.json"
            assert interactions_file.exists()
            interactions = json.loads(interactions_file.read_text())
            assert len(interactions) == 1
            assert interactions[0]["tool"] == "calculator"
            assert interactions[0]["session_id"] == session_id
            assert interactions[0]["status"] == "success"


# ── Interactions ──────────────────────────────────────────────────────────────

class TestInteractions:

    def test_list_interactions_empty(self, runner, authenticated):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "interactions", "list"])
            assert result.exit_code == 0

    def test_show_interaction_not_found(self, runner, authenticated):
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "interactions", "show", "nonexistent"])
            assert result.exit_code == 0
            assert "not found" in result.output

    def test_show_interaction_found(self, runner, authenticated):
        interaction_id = "test1234"
        interactions_file = authenticated / "interactions.json"
        interactions_file.write_text(json.dumps([{
            "id": interaction_id,
            "session_id": "abc12345",
            "tool": "calculator",
            "inputs": {"a": 1},
            "result": "42",
            "status": "success",
            "stdout": "",
            "user_inputs": [],
            "elapsed_ms": 10.0,
            "timestamp": "2026-01-01T00:00:00",
        }]))
        with patch("miminions.interface.cli.auth.get_config_dir", return_value=authenticated), \
             patch("miminions.interface.cli.execution.get_config_dir", return_value=authenticated):
            result = runner.invoke(cli, ["execution", "interactions", "show", interaction_id])
            assert result.exit_code == 0
            assert "calculator" in result.output
            assert "success" in result.output


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
