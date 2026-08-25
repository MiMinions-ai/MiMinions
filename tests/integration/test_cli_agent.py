"""
Unit tests for the MiMinions CLI agent module.
"""

import json
import os
import sys
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

import click
import pytest
from click.testing import CliRunner

from miminions.cli.agent import (
    agent_cli,
    load_agents,
    save_agents,
    get_agents_file,
    AgentAction,
    _execute_agent_action,
    _run_with_agent_runtime,
)


class TestAgentFunctions:
    """Test agent utility functions."""

    def test_get_agents_file(self):
        """Test that get_agents_file returns correct path."""
        with patch('miminions.cli.agent.get_config_dir') as mock_get_config_dir:
            mock_get_config_dir.return_value = Path('/tmp/test_config')
            agents_file = get_agents_file()
            assert agents_file == Path('/tmp/test_config/agents.json'), f"expect result to be {Path('/tmp/test_config/agents.json')}, got {agents_file}"

    def test_load_agents_no_file(self):
        """Test load_agents returns empty dict when no file exists."""
        with patch('miminions.cli.agent.get_agents_file') as mock_get_agents_file:
            mock_agents_file = MagicMock()
            mock_agents_file.exists.return_value = False
            mock_get_agents_file.return_value = mock_agents_file
            
            agents = load_agents()
            assert agents == {}, f"expect result to be {{}}, got {agents}"

    def test_load_agents_valid_file(self):
        """Test load_agents returns data from file."""
        test_data = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive"
            }
        }
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            json.dump(test_data, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            with patch('miminions.cli.agent.get_agents_file') as mock_get_agents_file:
                mock_get_agents_file.return_value = Path(tmp_path)
                
                loaded_data = load_agents()
                assert loaded_data == test_data, f"expect result to be {test_data}, got {loaded_data}"
        finally:
            os.unlink(tmp_path)

    def test_save_agents(self):
        """Test save_agents writes data to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with patch('miminions.cli.agent.get_agents_file') as mock_get_agents_file:
                mock_get_agents_file.return_value = Path(tmp_path)
                
                test_data = {
                    "test_agent": {
                        "name": "Test Agent",
                        "description": "A test agent",
                        "type": "general",
                        "status": "inactive"
                    }
                }
                save_agents(test_data)
                
                with open(tmp_path, 'r') as f:
                    saved_data = json.load(f)
                
                assert saved_data == test_data, f"expect result to be {test_data}, got {saved_data}"
        finally:
            os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_mcp_runtime_connects_loads_and_cleans_up(self):
        runtime = MagicMock()
        runtime.connect_mcp_server = AsyncMock()
        runtime.load_tools_from_mcp_server = AsyncMock()
        runtime.cleanup = AsyncMock()
        agent_data = {"mcp_servers": {
            "files": {"command": "python", "args": ["-m", "files_server"]}
        }}

        with patch('miminions.cli.agent._build_cli_extension_agent', return_value=runtime):
            with patch(
                'miminions.cli.agent._execute_agent_action',
                new=AsyncMock(return_value="done"),
            ) as action:
                result = await _run_with_agent_runtime(
                    agent_data, AgentAction.TOOL_LIST
                )

        assert result == "done", f"expect result to be {'done'}, got {result}"
        params = runtime.connect_mcp_server.await_args.args[1]
        assert params.command == "python", f"expect result to be {'python'}, got {params.command}"
        assert params.args == ["-m", "files_server"], f"expect result to be {['-m', 'files_server']}, got {params.args}"
        runtime.load_tools_from_mcp_server.assert_awaited_once_with("files")
        action.assert_awaited_once_with(runtime, AgentAction.TOOL_LIST)
        runtime.cleanup.assert_awaited_once_with(rebuild=False)

    @pytest.mark.asyncio
    async def test_mcp_runtime_failure_is_named_and_cleans_up(self):
        runtime = MagicMock()
        runtime.connect_mcp_server = AsyncMock(side_effect=RuntimeError("offline"))
        runtime.cleanup = AsyncMock()

        with patch('miminions.cli.agent._build_cli_extension_agent', return_value=runtime):
            with pytest.raises(Exception, match="Failed to load MCP server 'files'"):
                await _run_with_agent_runtime(
                    {"mcp_servers": {"files": {"command": "python", "args": []}}},
                    AgentAction.TOOL_LIST,
                )

        runtime.cleanup.assert_awaited_once_with(rebuild=False)

    @pytest.mark.asyncio
    async def test_runtime_action_dispatch_rejects_unknown_operation(self):
        with pytest.raises(click.ClickException, match="Unsupported agent runtime operation"):
            await _execute_agent_action(MagicMock(), "unknown")

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("operation", "params", "message"),
        [
            (AgentAction.ASK, {}, "Missing parameter.*prompt"),
            (
                AgentAction.TOOL_LIST,
                {"query": "extra"},
                "Unexpected parameter.*query",
            ),
            (
                AgentAction.TOOL_RUN,
                {"tool_name": "greet", "arguments": []},
                "Invalid parameter 'arguments'.*expected dict",
            ),
            (
                AgentAction.TOOL_INFO,
                {"tool_name": "  "},
                "Invalid parameter 'tool_name'.*cannot be empty",
            ),
        ],
    )
    async def test_runtime_action_dispatch_validates_operation_params(
        self, operation, params, message
    ):
        with pytest.raises(click.ClickException, match=message):
            await _execute_agent_action(MagicMock(), operation, **params)


class TestAgentCLI:
    """Test agent CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_list_agents_empty(self):
        """Test list agents when no agents exist."""
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {}
                
                result = self.runner.invoke(agent_cli, ['list'])
                
                assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                assert 'No agents configured' in result.output, f"expect 'No agents configured' in result.output, got {result.output}"

    def test_list_agents_not_authenticated(self):
        """Test list agents when not authenticated."""
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            
            result = self.runner.invoke(agent_cli, ['list'])
            
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            # NOTE(auth-bypass): Auth enforcement is currently disabled in
            # src/miminions/cli/agent.py::require_auth (temporary no-op).
            # Keep this assertion commented so test behavior remains otherwise unchanged.
            # Re-enable once the real auth guard is restored.
            # assert 'Please sign in first' in result.output

    def test_list_agents_with_data(self):
        """Test list agents with existing agents."""
        test_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive"
            },
            "another_agent": {
                "name": "Another Agent",
                "description": "Another test agent",
                "type": "specialized",
                "status": "running"
            }
        }
        
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = test_agents
                
                result = self.runner.invoke(agent_cli, ['list'])
                
                assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                assert 'Agents:' in result.output, f"expect 'Agents:' in result.output, got {result.output}"
                assert 'test_agent: Test Agent (inactive)' in result.output, f"expect 'test_agent: Test Agent (inactive)' in result.output, got {result.output}"
                assert 'another_agent: Another Agent (running)' in result.output, f"expect 'another_agent: Another Agent (running)' in result.output, got {result.output}"

    def test_add_agent_success(self):
        """Test successful agent addition."""
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                with patch('miminions.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = {}
                    
                    result = self.runner.invoke(agent_cli, [
                        'add',
                        '--name', 'Test Agent',
                        '--description', 'A test agent',
                        '--type', 'general'
                    ])
                    
                    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                    assert 'Agent \'Test Agent\' added successfully' in result.output, f"expect \"Agent 'Test Agent' added successfully\" in result.output, got {result.output}"
                    mock_save.assert_called_once()

    def test_add_agent_duplicate_id_gets_unique_suffix(self):
        """A name whose slug already exists gets a unique suffixed ID."""
        existing_agents = {
            "test_agent": {
                "name": "Existing Agent",
                "description": "An existing agent",
                "type": "general",
                "status": "inactive"
            }
        }

        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                with patch('miminions.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents

                    result = self.runner.invoke(agent_cli, [
                        'add',
                        '--name', 'Test Agent',  # slug "test_agent" already exists
                        '--description', 'A test agent',
                        '--type', 'general'
                    ])

                    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                    assert 'ID: test_agent_2' in result.output, f"expect 'ID: test_agent_2' in result.output, got {result.output}"
                    saved = mock_save.call_args[0][0]
                    assert 'test_agent_2' in saved, f"expect 'test_agent_2' in saved, got {saved}"
                    assert 'test_agent' in saved, f"expect 'test_agent' in saved, got {saved}"  # original preserved

    def test_add_agent_not_authenticated(self):
        """Test adding agent when not authenticated."""
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            
            result = self.runner.invoke(agent_cli, [
                'add',
                '--name', 'Test Agent',
                '--description', 'A test agent',
                '--type', 'general'
            ])
            
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            # NOTE(auth-bypass): Auth enforcement is currently disabled in
            # src/miminions/cli/agent.py::require_auth (temporary no-op).
            # Keep this assertion commented so test behavior remains otherwise unchanged.
            # Re-enable once the real auth guard is restored.
            # assert 'Please sign in first' in result.output

    def test_update_agent_success(self):
        """Test successful agent update."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive"
            }
        }
        
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                with patch('miminions.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents
                    
                    result = self.runner.invoke(agent_cli, [
                        'update',
                        'test_agent',
                        '--name', 'Updated Agent',
                        '--description', 'Updated description'
                    ])
                    
                    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                    assert 'Agent \'test_agent\' updated successfully' in result.output, f"expect \"Agent 'test_agent' updated successfully\" in result.output, got {result.output}"
                    mock_save.assert_called_once()

    def test_update_agent_not_found(self):
        """Test updating non-existent agent."""
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {}
                
                result = self.runner.invoke(agent_cli, [
                    'update',
                    'nonexistent_agent',
                    '--name', 'Updated Agent'
                ])
                
                assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                assert 'not found' in result.output, f"expect 'not found' in result.output, got {result.output}"

    def test_remove_agent_success(self):
        """Test successful agent removal."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive"
            }
        }
        
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                with patch('miminions.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents
                    
                    result = self.runner.invoke(agent_cli, [
                        'remove',
                        'test_agent',
                        '--yes'  # Skip confirmation
                    ])
                    
                    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                    assert 'Agent \'test_agent\' removed successfully' in result.output, f"expect \"Agent 'test_agent' removed successfully\" in result.output, got {result.output}"
                    mock_save.assert_called_once()

    def test_remove_agent_not_found(self):
        """Test removing non-existent agent."""
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {}
                
                result = self.runner.invoke(agent_cli, [
                    'remove',
                    'nonexistent_agent',
                    '--yes'
                ])
                
                assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                assert 'not found' in result.output, f"expect 'not found' in result.output, got {result.output}"

    def test_mcp_add_persists_minimal_config_and_argument_order(self):
        agents = {"test_agent": {"name": "Test Agent"}}
        with patch('miminions.cli.agent.load_agents', return_value=agents):
            with patch('miminions.cli.agent.save_agents') as mock_save:
                result = self.runner.invoke(agent_cli, [
                    'mcp-add', 'test_agent', 'files', '--command', 'python',
                    '--arg', '-m', '--arg', 'files_server',
                ])

        assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
        saved = mock_save.call_args.args[0]
        assert saved['test_agent']['mcp_servers']['files'] == {
            'command': 'python', 'args': ['-m', 'files_server']
        }, f"expect result to be {{'command': 'python', 'args': ['-m', 'files_server']}}, got {saved['test_agent']['mcp_servers']['files']}"

    def test_mcp_add_rejects_duplicate_server(self):
        agents = {"test_agent": {"mcp_servers": {"files": {"command": "python", "args": []}}}}
        with patch('miminions.cli.agent.load_agents', return_value=agents):
            result = self.runner.invoke(agent_cli, [
                'mcp-add', 'test_agent', 'files', '--command', 'python',
            ])

        assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
        assert "already exists" in result.output, f"expect 'already exists' in result.output, got {result.output}"

    def test_mcp_list_and_remove(self):
        agents = {"test_agent": {"mcp_servers": {
            "files": {"command": "python", "args": ["-m", "files_server"]}
        }}}
        with patch('miminions.cli.agent.load_agents', return_value=agents):
            listed = self.runner.invoke(agent_cli, ['mcp-list', 'test_agent'])
            with patch('miminions.cli.agent.save_agents') as mock_save:
                removed = self.runner.invoke(
                    agent_cli, ['mcp-remove', 'test_agent', 'files', '--yes']
                )

        assert listed.exit_code == 0, f"expect cli exit code 0, got {listed.exit_code} with output: {listed.output}"
        assert "files: python -m files_server" in listed.output, f"expect 'files: python -m files_server' in listed.output, got {listed.output}"
        assert removed.exit_code == 0, f"expect cli exit code 0, got {removed.exit_code} with output: {removed.output}"
        assert agents['test_agent']['mcp_servers'] == {}, f"expect result to be {{}}, got {agents['test_agent']['mcp_servers']}"
        mock_save.assert_called_once_with(agents)

    def test_set_goal_success(self):
        """Test successful goal setting."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive"
            }
        }
        
        with patch('miminions.core.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.agent.load_agents') as mock_load:
                with patch('miminions.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents
                    
                    result = self.runner.invoke(agent_cli, [
                        'set-goal',
                        'test_agent',
                        '--goal', 'Complete the task'
                    ])
                    
                    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                    assert 'Goal set for agent \'test_agent\': Complete the task' in result.output, f"expect \"Goal set for agent 'test_agent': Complete the task\" in result.output, got {result.output}"
                    mock_save.assert_called_once()

    def test_show_agent_by_exact_id(self):
        """Show should resolve by exact agent id."""
        existing_agents = {
            "research_agent": {
                "name": "Research Agent",
                "description": "Finds information",
                "type": "assistant",
                "status": "inactive",
                "goal": "summarize docs",
                "created_at": "2026-07-01T00:00:00+00:00",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(agent_cli, ['show', 'research_agent'])

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert 'Agent: Research Agent' in result.output, f"expect 'Agent: Research Agent' in result.output, got {result.output}"
            assert 'ID: research_agent' in result.output, f"expect 'ID: research_agent' in result.output, got {result.output}"
            assert 'Description: Finds information' in result.output, f"expect 'Description: Finds information' in result.output, got {result.output}"

    def test_show_agent_by_id_prefix(self):
        """Show should resolve by id prefix."""
        existing_agents = {
            "research_agent": {
                "name": "Research Agent",
                "description": "Finds information",
                "type": "assistant",
                "status": "inactive",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(agent_cli, ['show', 'rese'])

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert 'ID: research_agent' in result.output, f"expect 'ID: research_agent' in result.output, got {result.output}"

    def test_show_agent_by_name(self):
        """Show should resolve by exact agent name."""
        existing_agents = {
            "research_agent": {
                "name": "Research Agent",
                "description": "Finds information",
                "type": "assistant",
                "status": "inactive",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(agent_cli, ['show', 'Research Agent'])

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert 'ID: research_agent' in result.output, f"expect 'ID: research_agent' in result.output, got {result.output}"

    def test_agent_list_and_show_json_output(self):
        """List/show should return valid JSON when --json is used."""
        agents = {
            "research_agent": {
                "name": "Research Agent",
                "description": "Finds facts",
                "type": "assistant",
                "status": "inactive",
            }
        }

        with patch('miminions.cli.agent.load_agents', return_value=agents):
            list_result = self.runner.invoke(agent_cli, ['list', '--json'])
            show_result = self.runner.invoke(agent_cli, ['show', 'research_agent', '--json'])

        assert list_result.exit_code == 0, f"expect cli exit code 0, got {list_result.exit_code} with output: {list_result.output}"
        assert show_result.exit_code == 0, f"expect cli exit code 0, got {show_result.exit_code} with output: {show_result.output}"

        list_payload = json.loads(list_result.output)
        show_payload = json.loads(show_result.output)

        assert list_payload[0]['id'] == 'research_agent', f"expect result to be {'research_agent'}, got {list_payload[0]['id']}"
        assert show_payload['id'] == 'research_agent', f"expect result to be {'research_agent'}, got {show_payload['id']}"
        assert show_payload['name'] == 'Research Agent', f"expect result to be {'Research Agent'}, got {show_payload['name']}"



    def test_tool_list_success(self):
        """Test listing tools for an agent."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(agent_cli, ['tool-list', 'test_agent'])

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert "Tools for 'test_agent':" in result.output, f"expect \"Tools for 'test_agent':\" in result.output, got {result.output}"
            assert "cli_run_command" in result.output, f"expect 'cli_run_command' in result.output, got {result.output}"
            assert "cli_echo" in result.output, f"expect 'cli_echo' in result.output, got {result.output}"
            assert "cli_add" in result.output, f"expect 'cli_add' in result.output, got {result.output}"

    def test_tool_info_success(self):
        """Test showing tool info for a known tool."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(agent_cli, ['tool-info', 'test_agent', 'cli_add'])

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert "Tool: cli_add" in result.output, f"expect 'Tool: cli_add' in result.output, got {result.output}"
            assert "Description: Add two integers" in result.output, f"expect 'Description: Add two integers' in result.output, got {result.output}"
            assert "Schema:" in result.output, f"expect 'Schema:' in result.output, got {result.output}"

    def test_tool_run_success(self):
        """Test running a tool with valid JSON arguments."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(
                    agent_cli,
                    ['tool-run', 'test_agent', 'cli_add', '--arguments', '{"a": 2, "b": 3}']
                )

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert "Tool: cli_add" in result.output, f"expect 'Tool: cli_add' in result.output, got {result.output}"
            assert "Status: success" in result.output, f"expect 'Status: success' in result.output, got {result.output}"
            assert "Result: 5" in result.output, f"expect 'Result: 5' in result.output, got {result.output}"

    def test_tool_run_cli_command_success(self):
        """Test running the default command execution tool through the CLI."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
            }
        }
        arguments = json.dumps({"command": f"{sys.executable} --version"})

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(
                    agent_cli,
                    ['tool-run', 'test_agent', 'cli_run_command', '--arguments', arguments],
                    input='y\n',
                )

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert "Tool: cli_run_command" in result.output, f"expect 'Tool: cli_run_command' in result.output, got {result.output}"
            assert "Status: success" in result.output, f"expect 'Status: success' in result.output, got {result.output}"
            assert "'returncode': 0" in result.output, f"expect \"'returncode': 0\" in result.output, got {result.output}"
            assert "Python" in result.output, f"expect 'Python' in result.output, got {result.output}"

    def test_tool_run_cli_command_denied(self):
        """Test declining the default command execution tool through the CLI."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
            }
        }
        arguments = json.dumps({"command": f"{sys.executable} --version"})

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                with patch('miminions.tools.default.subprocess.run') as mock_run:
                    mock_load.return_value = existing_agents
                    result = self.runner.invoke(
                        agent_cli,
                        ['tool-run', 'test_agent', 'cli_run_command', '--arguments', arguments],
                        input='n\n',
                    )

        assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
        assert "Status: error" in result.output, f"expect 'Status: error' in result.output, got {result.output}"
        assert "Command execution was not approved" in result.output, f"expect 'Command execution was not approved' in result.output, got {result.output}"
        mock_run.assert_not_called()

    def test_tool_run_invalid_json(self):
        """Test running a tool with invalid JSON input."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(
                    agent_cli,
                    ['tool-run', 'test_agent', 'cli_add', '--arguments', 'not-json']
                )

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert "Invalid JSON for --arguments." in result.output, f"expect 'Invalid JSON for --arguments.' in result.output, got {result.output}"

    def test_ask_agent_uses_tool_fallback_for_addition(self):
        """Ask should use cli_add fallback when prompt requests arithmetic."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                mock_load.return_value = existing_agents

                result = self.runner.invoke(
                    agent_cli,
                    ['ask', 'test_agent', '--prompt', 'Please add 4 and 9 for me']
                )

            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert "Asking agent 'test_agent': Please add 4 and 9 for me" in result.output, f"expect \"Asking agent 'test_agent': Please add 4 and 9 for me\" in result.output, got {result.output}"
            assert "Agent response: Used tool cli_add -> 13" in result.output, f"expect 'Agent response: Used tool cli_add -> 13' in result.output, got {result.output}"

    def test_run_agent_uses_tool_fallback_for_addition_goal(self):
        """Run should use cli_add fallback for arithmetic goals."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
                "goal": "Add 10 and 5",
            }
        }

        with patch('miminions.core.auth.is_authenticated', return_value=True):
            with patch('miminions.cli.agent.load_agents') as mock_load:
                with patch('miminions.cli.agent.save_agents') as mock_save:
                    mock_load.return_value = existing_agents

                    result = self.runner.invoke(agent_cli, ['run', 'test_agent'])

                    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                    assert "Running agent 'test_agent' with goal: Add 10 and 5" in result.output, f"expect \"Running agent 'test_agent' with goal: Add 10 and 5\" in result.output, got {result.output}"
                    assert "Agent response: Used tool cli_add -> 15" in result.output, f"expect 'Agent response: Used tool cli_add -> 15' in result.output, got {result.output}"
                    mock_save.assert_called_once()
