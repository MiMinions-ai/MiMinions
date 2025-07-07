"""
Unit tests for the MiMinions CLI agent module.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from interface.cli.agent import agent_cli, load_agents, save_agents, get_agents_file


class TestAgentFunctions:
    """Test agent utility functions."""

    def test_get_agents_file(self):
        """Test that get_agents_file returns correct path."""
        with patch('interface.cli.agent.get_config_dir') as mock_get_config_dir:
            mock_get_config_dir.return_value = Path('/tmp/test_config')
            agents_file = get_agents_file()
            assert agents_file == Path('/tmp/test_config/agents.json')

    def test_load_agents_no_file(self):
        """Test load_agents returns empty dict when no file exists."""
        with patch('interface.cli.agent.get_agents_file') as mock_get_agents_file:
            mock_agents_file = MagicMock()
            mock_agents_file.exists.return_value = False
            mock_get_agents_file.return_value = mock_agents_file
            
            agents = load_agents()
            assert agents == {}

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
            with patch('interface.cli.agent.get_agents_file') as mock_get_agents_file:
                mock_get_agents_file.return_value = Path(tmp_path)
                
                loaded_data = load_agents()
                assert loaded_data == test_data
        finally:
            os.unlink(tmp_path)

    def test_save_agents(self):
        """Test save_agents writes data to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with patch('interface.cli.agent.get_agents_file') as mock_get_agents_file:
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
                
                assert saved_data == test_data
        finally:
            os.unlink(tmp_path)


class TestAgentCLI:
    """Test agent CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_list_agents_empty(self):
        """Test list agents when no agents exist."""
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {}
                
                result = self.runner.invoke(agent_cli, ['list'])
                
                assert result.exit_code == 0
                assert 'No agents configured' in result.output

    def test_list_agents_not_authenticated(self):
        """Test list agents when not authenticated."""
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            
            result = self.runner.invoke(agent_cli, ['list'])
            
            assert result.exit_code == 0
            assert 'Please sign in first' in result.output

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
        
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = test_agents
                
                result = self.runner.invoke(agent_cli, ['list'])
                
                assert result.exit_code == 0
                assert 'Agents:' in result.output
                assert 'test_agent: Test Agent (inactive)' in result.output
                assert 'another_agent: Another Agent (running)' in result.output

    def test_add_agent_success(self):
        """Test successful agent addition."""
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                with patch('interface.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = {}
                    
                    result = self.runner.invoke(agent_cli, [
                        'add',
                        '--name', 'Test Agent',
                        '--description', 'A test agent',
                        '--type', 'general'
                    ])
                    
                    assert result.exit_code == 0
                    assert 'Agent \'Test Agent\' added successfully' in result.output
                    mock_save.assert_called_once()

    def test_add_agent_duplicate(self):
        """Test adding agent with duplicate ID."""
        existing_agents = {
            "test_agent": {
                "name": "Existing Agent",
                "description": "An existing agent",
                "type": "general",
                "status": "inactive"
            }
        }
        
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = existing_agents
                
                result = self.runner.invoke(agent_cli, [
                    'add',
                    '--name', 'Test Agent',  # This will create ID "test_agent"
                    '--description', 'A test agent',
                    '--type', 'general'
                ])
                
                assert result.exit_code == 0
                assert 'already exists' in result.output

    def test_add_agent_not_authenticated(self):
        """Test adding agent when not authenticated."""
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            
            result = self.runner.invoke(agent_cli, [
                'add',
                '--name', 'Test Agent',
                '--description', 'A test agent',
                '--type', 'general'
            ])
            
            assert result.exit_code == 0
            assert 'Please sign in first' in result.output

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
        
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                with patch('interface.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents
                    
                    result = self.runner.invoke(agent_cli, [
                        'update',
                        'test_agent',
                        '--name', 'Updated Agent',
                        '--description', 'Updated description'
                    ])
                    
                    assert result.exit_code == 0
                    assert 'Agent \'test_agent\' updated successfully' in result.output
                    mock_save.assert_called_once()

    def test_update_agent_not_found(self):
        """Test updating non-existent agent."""
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {}
                
                result = self.runner.invoke(agent_cli, [
                    'update',
                    'nonexistent_agent',
                    '--name', 'Updated Agent'
                ])
                
                assert result.exit_code == 0
                assert 'not found' in result.output

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
        
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                with patch('interface.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents
                    
                    result = self.runner.invoke(agent_cli, [
                        'remove',
                        'test_agent',
                        '--yes'  # Skip confirmation
                    ])
                    
                    assert result.exit_code == 0
                    assert 'Agent \'test_agent\' removed successfully' in result.output
                    mock_save.assert_called_once()

    def test_remove_agent_not_found(self):
        """Test removing non-existent agent."""
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {}
                
                result = self.runner.invoke(agent_cli, [
                    'remove',
                    'nonexistent_agent',
                    '--yes'
                ])
                
                assert result.exit_code == 0
                assert 'not found' in result.output

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
        
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                with patch('interface.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents
                    
                    result = self.runner.invoke(agent_cli, [
                        'set-goal',
                        'test_agent',
                        '--goal', 'Complete the task'
                    ])
                    
                    assert result.exit_code == 0
                    assert 'Goal set for agent \'test_agent\': Complete the task' in result.output
                    mock_save.assert_called_once()

    def test_run_agent_success(self):
        """Test successful agent run."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
                "goal": "Complete the task"
            }
        }
        
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                with patch('interface.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents
                    
                    result = self.runner.invoke(agent_cli, [
                        'run',
                        'test_agent'
                    ])
                    
                    assert result.exit_code == 0
                    assert 'Running agent \'test_agent\' with goal: Complete the task' in result.output
                    mock_save.assert_called_once()

    def test_run_agent_no_goal(self):
        """Test running agent without goal."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive"
            }
        }
        
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = existing_agents
                
                result = self.runner.invoke(agent_cli, [
                    'run',
                    'test_agent'
                ])
                
                assert result.exit_code == 0
                assert 'has no goal set' in result.output

    def test_run_agent_async(self):
        """Test running agent asynchronously."""
        existing_agents = {
            "test_agent": {
                "name": "Test Agent",
                "description": "A test agent",
                "type": "general",
                "status": "inactive",
                "goal": "Complete the task"
            }
        }
        
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                with patch('interface.cli.agent.save_agents') as mock_save:
                    mock_is_auth.return_value = True
                    mock_load.return_value = existing_agents
                    
                    result = self.runner.invoke(agent_cli, [
                        'run',
                        'test_agent',
                        '--async'
                    ])
                    
                    assert result.exit_code == 0
                    assert 'Agent \'test_agent\' started asynchronously' in result.output
                    mock_save.assert_called_once()