"""
End-to-end tests for the MiMinions CLI.
These tests simulate real user workflows and interactions.
"""

import pytest
import tempfile
import os
import json
from pathlib import Path
from unittest.mock import patch
from click.testing import CliRunner

from miminions.interface.cli.main import cli


class TestCLIEndToEnd:
    """End-to-end tests for the complete CLI workflow."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()
        self.config_dir = Path(self.temp_dir) / ".miminions"
        self.config_dir.mkdir(exist_ok=True)

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_workflow(self):
        """Test a complete workflow from authentication to agent execution."""
        with patch('miminions.interface.cli.auth.get_config_dir') as mock_config_dir:
            mock_config_dir.return_value = self.config_dir
            
            # Step 1: Check initial status (should be not authenticated)
            result = self.runner.invoke(cli, ['auth', 'status'])
            assert result.exit_code == 0
            assert 'Not signed in' in result.output
            
            # Step 2: Sign in
            result = self.runner.invoke(cli, [
                'auth', 'signin',
                '--username', 'testuser',
                '--password', 'testpass'
            ])
            assert result.exit_code == 0
            assert 'Successfully signed in as testuser' in result.output
            
            # Step 3: Check status after signin
            result = self.runner.invoke(cli, ['auth', 'status'])
            assert result.exit_code == 0
            assert 'Signed in as: testuser' in result.output
            
            # Step 4: List agents (should be empty)
            result = self.runner.invoke(cli, ['agent', 'list'])
            assert result.exit_code == 0
            assert 'No agents configured' in result.output
            
            # Step 5: Add an agent
            result = self.runner.invoke(cli, [
                'agent', 'add',
                '--name', 'Test Agent',
                '--description', 'A test agent for e2e testing',
                '--type', 'general'
            ])
            assert result.exit_code == 0
            assert 'Agent \'Test Agent\' added successfully' in result.output
            
            # Step 6: List agents (should have one agent)
            result = self.runner.invoke(cli, ['agent', 'list'])
            assert result.exit_code == 0
            assert 'test_agent: Test Agent (inactive)' in result.output
            
            # Step 7: Set goal for the agent
            result = self.runner.invoke(cli, [
                'agent', 'set-goal',
                'test_agent',
                '--goal', 'Complete the e2e test'
            ])
            assert result.exit_code == 0
            assert 'Goal set for agent \'test_agent\': Complete the e2e test' in result.output
            
            # Step 8: Run the agent
            result = self.runner.invoke(cli, [
                'agent', 'run',
                'test_agent'
            ])
            assert result.exit_code == 0
            assert 'Running agent \'test_agent\' with goal: Complete the e2e test' in result.output
            
            # Step 9: Add a task
            result = self.runner.invoke(cli, [
                'task', 'add',
                '--title', 'Test Task',
                '--description', 'A test task for e2e testing',
                '--priority', 'high',
                '--agent', 'test_agent'
            ])
            assert result.exit_code == 0
            assert 'Task \'Test Task\' added successfully' in result.output
            
            # Step 10: List tasks
            result = self.runner.invoke(cli, ['task', 'list'])
            assert result.exit_code == 0
            assert 'Test Task (pending, high)' in result.output
            
            # Step 11: Add a workflow
            result = self.runner.invoke(cli, [
                'workflow', 'add',
                '--name', 'Test Workflow',
                '--description', 'A test workflow for e2e testing',
                '--agents', 'test_agent'
            ])
            assert result.exit_code == 0
            assert 'Workflow \'Test Workflow\' added successfully' in result.output
            
            # Step 12: Start the workflow
            workflow_id = self._extract_workflow_id(result.output)
            result = self.runner.invoke(cli, [
                'workflow', 'start',
                workflow_id
            ])
            assert result.exit_code == 0
            assert f'Workflow \'{workflow_id}\' started successfully' in result.output
            
            # Step 13: Add knowledge
            result = self.runner.invoke(cli, [
                'knowledge', 'add',
                '--title', 'Test Knowledge',
                '--content', 'This is test knowledge content',
                '--category', 'testing',
                '--tags', 'test,e2e'
            ])
            assert result.exit_code == 0
            assert 'Knowledge entry \'Test Knowledge\' added successfully' in result.output
            
            # Step 14: List knowledge
            result = self.runner.invoke(cli, ['knowledge', 'list'])
            assert result.exit_code == 0
            assert 'Test Knowledge (v1.0, testing, active)' in result.output
            
            # Step 15: Sign out
            result = self.runner.invoke(cli, ['auth', 'signout'])
            assert result.exit_code == 0
            assert 'Successfully signed out testuser' in result.output
            
            # Step 16: Verify signed out
            result = self.runner.invoke(cli, ['auth', 'status'])
            assert result.exit_code == 0
            assert 'Not signed in' in result.output

    def test_authentication_required_workflow(self):
        """Test that commands requiring authentication are properly blocked."""
        with patch('miminions.interface.cli.auth.get_config_dir') as mock_config_dir:
            mock_config_dir.return_value = self.config_dir
            
            # Try to list agents without authentication
            result = self.runner.invoke(cli, ['agent', 'list'])
            assert result.exit_code == 0
            assert 'Please sign in first' in result.output
            
            # Try to add task without authentication
            result = self.runner.invoke(cli, [
                'task', 'add',
                '--title', 'Test Task',
                '--description', 'A test task'
            ])
            assert result.exit_code == 0
            assert 'Please sign in first' in result.output
            
            # Try to list workflows without authentication
            result = self.runner.invoke(cli, ['workflow', 'list'])
            assert result.exit_code == 0
            assert 'Please sign in first' in result.output
            
            # Try to list knowledge without authentication
            result = self.runner.invoke(cli, ['knowledge', 'list'])
            assert result.exit_code == 0
            assert 'Please sign in first' in result.output

    def test_data_persistence_workflow(self):
        """Test that data persists across CLI invocations."""
        with patch('miminions.interface.cli.auth.get_config_dir') as mock_config_dir:
            mock_config_dir.return_value = self.config_dir
            
            # Sign in and add an agent
            self.runner.invoke(cli, [
                'auth', 'signin',
                '--username', 'testuser',
                '--password', 'testpass'
            ])
            
            result = self.runner.invoke(cli, [
                'agent', 'add',
                '--name', 'Persistent Agent',
                '--description', 'Agent to test persistence',
                '--type', 'general'
            ])
            assert result.exit_code == 0
            
            # Verify the agent was saved by checking the file directly
            agents_file = self.config_dir / "agents.json"
            assert agents_file.exists()
            
            with open(agents_file, 'r') as f:
                agents_data = json.load(f)
            
            assert 'persistent_agent' in agents_data
            assert agents_data['persistent_agent']['name'] == 'Persistent Agent'
            
            # Verify the agent can be listed in a new CLI invocation
            result = self.runner.invoke(cli, ['agent', 'list'])
            assert result.exit_code == 0
            assert 'persistent_agent: Persistent Agent (inactive)' in result.output

    def test_error_handling_workflow(self):
        """Test proper error handling in various scenarios."""
        with patch('miminions.interface.cli.auth.get_config_dir') as mock_config_dir:
            mock_config_dir.return_value = self.config_dir
            
            # Sign in first
            self.runner.invoke(cli, [
                'auth', 'signin',
                '--username', 'testuser',
                '--password', 'testpass'
            ])
            
            # Try to update non-existent agent
            result = self.runner.invoke(cli, [
                'agent', 'update',
                'nonexistent_agent',
                '--name', 'Updated Name'
            ])
            assert result.exit_code == 0
            assert 'not found' in result.output
            
            # Try to remove non-existent task
            result = self.runner.invoke(cli, [
                'task', 'remove',
                'nonexistent_task',
                '--yes'
            ])
            assert result.exit_code == 0
            assert 'not found' in result.output
            
            # Try to start non-existent workflow
            result = self.runner.invoke(cli, [
                'workflow', 'start',
                'nonexistent_workflow'
            ])
            assert result.exit_code == 0
            assert 'not found' in result.output
            
            # Try to show non-existent knowledge
            result = self.runner.invoke(cli, [
                'knowledge', 'show',
                'nonexistent_knowledge'
            ])
            assert result.exit_code == 0
            assert 'not found' in result.output

    def test_task_management_workflow(self):
        """Test complete task management workflow."""
        with patch('miminions.interface.cli.auth.get_config_dir') as mock_config_dir:
            mock_config_dir.return_value = self.config_dir
            
            # Sign in
            self.runner.invoke(cli, [
                'auth', 'signin',
                '--username', 'testuser',
                '--password', 'testpass'
            ])
            
            # Add a task
            result = self.runner.invoke(cli, [
                'task', 'add',
                '--title', 'Original Task',
                '--description', 'Original description',
                '--priority', 'medium'
            ])
            assert result.exit_code == 0
            task_id = self._extract_task_id(result.output)
            
            # Update the task
            result = self.runner.invoke(cli, [
                'task', 'update',
                task_id,
                '--title', 'Updated Task',
                '--status', 'in_progress'
            ])
            assert result.exit_code == 0
            
            # Show the updated task
            result = self.runner.invoke(cli, [
                'task', 'show',
                task_id
            ])
            assert result.exit_code == 0
            assert 'Updated Task' in result.output
            assert 'in_progress' in result.output
            
            # Duplicate the task
            result = self.runner.invoke(cli, [
                'task', 'duplicate',
                task_id,
                '--title', 'Duplicated Task'
            ])
            assert result.exit_code == 0
            
            # List tasks (should have 2 tasks)
            result = self.runner.invoke(cli, ['task', 'list'])
            assert result.exit_code == 0
            assert 'Updated Task' in result.output
            assert 'Duplicated Task' in result.output

    def test_knowledge_versioning_workflow(self):
        """Test knowledge versioning workflow."""
        with patch('miminions.interface.cli.auth.get_config_dir') as mock_config_dir:
            mock_config_dir.return_value = self.config_dir
            
            # Sign in
            self.runner.invoke(cli, [
                'auth', 'signin',
                '--username', 'testuser',
                '--password', 'testpass'
            ])
            
            # Add knowledge
            result = self.runner.invoke(cli, [
                'knowledge', 'add',
                '--title', 'Versioned Knowledge',
                '--content', 'Original content',
                '--category', 'testing'
            ])
            assert result.exit_code == 0
            entry_id = self._extract_knowledge_id(result.output)
            
            # Update the knowledge (should create new version)
            result = self.runner.invoke(cli, [
                'knowledge', 'update',
                entry_id,
                '--content', 'Updated content'
            ])
            assert result.exit_code == 0
            
            # Check version history
            result = self.runner.invoke(cli, [
                'knowledge', 'version',
                entry_id
            ])
            assert result.exit_code == 0
            assert 'v1.0' in result.output
            assert 'v1.1' in result.output
            assert '(current)' in result.output
            
            # Revert to previous version
            result = self.runner.invoke(cli, [
                'knowledge', 'revert',
                entry_id,
                '--version', '1.0'
            ])
            assert result.exit_code == 0
            
            # Verify reverted content
            result = self.runner.invoke(cli, [
                'knowledge', 'show',
                entry_id
            ])
            assert result.exit_code == 0
            assert 'Original content' in result.output

    def _extract_workflow_id(self, output):
        """Extract workflow ID from command output."""
        # Look for pattern like "with ID: xxxxxxxx"
        import re
        match = re.search(r'with ID: (\w+)', output)
        return match.group(1) if match else 'unknown'

    def _extract_task_id(self, output):
        """Extract task ID from command output."""
        # Look for pattern like "with ID: xxxxxxxx"
        import re
        match = re.search(r'with ID: (\w+)', output)
        return match.group(1) if match else 'unknown'

    def _extract_knowledge_id(self, output):
        """Extract knowledge entry ID from command output."""
        # Look for pattern like "with ID: xxxxxxxx"
        import re
        match = re.search(r'with ID: (\w+)', output)
        return match.group(1) if match else 'unknown'