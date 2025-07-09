"""
Simple test runner for the CLI tests.
This can be used to run tests without pytest if needed.
"""

import sys
import os
import subprocess

# Add src to path so we can import the modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

def run_basic_test():
    """Run a basic test to verify the CLI works."""
    try:
        from interface.cli.main import cli
        from click.testing import CliRunner
        from unittest.mock import patch
        import tempfile
        from pathlib import Path
        
        runner = CliRunner()
        temp_dir = tempfile.mkdtemp()
        config_dir = Path(temp_dir) / ".miminions"
        config_dir.mkdir(exist_ok=True)
        
        # Test basic CLI functionality
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'MiMinions CLI' in result.output
        
        # Test auth status when not signed in (with isolated config)
        with patch('interface.cli.auth.get_config_dir') as mock_config_dir:
            mock_config_dir.return_value = config_dir
            result = runner.invoke(cli, ['auth', 'status'])
            assert result.exit_code == 0
            assert 'Not signed in' in result.output
        
        print("✓ Basic CLI tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Basic CLI test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

def run_auth_test():
    """Run authentication tests."""
    try:
        from interface.cli.auth import auth_cli
        from click.testing import CliRunner
        from unittest.mock import patch
        
        runner = CliRunner()
        
        # Test signin
        with patch('interface.cli.auth.save_auth_data') as mock_save:
            result = runner.invoke(auth_cli, ['signin', '--username', 'testuser', '--password', 'testpass'])
            assert result.exit_code == 0
            assert 'Successfully signed in as testuser' in result.output
            mock_save.assert_called_once()
        
        print("✓ Authentication tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Authentication test failed: {e}")
        return False

def run_agent_test():
    """Run agent management tests."""
    try:
        from interface.cli.agent import agent_cli
        from click.testing import CliRunner
        from unittest.mock import patch
        
        runner = CliRunner()
        
        # Test list agents when not authenticated
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            result = runner.invoke(agent_cli, ['list'])
            assert result.exit_code == 0
            assert 'Please sign in first' in result.output
        
        # Test list agents when authenticated but no agents
        with patch('interface.cli.agent.is_authenticated') as mock_is_auth:
            with patch('interface.cli.agent.load_agents') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {}
                result = runner.invoke(agent_cli, ['list'])
                assert result.exit_code == 0
                assert 'No agents configured' in result.output
        
        print("✓ Agent management tests passed")
        return True
        
    except Exception as e:
        print(f"✗ Agent management test failed: {e}")
        return False

def main():
    """Run all basic tests."""
    print("Running CLI tests...")
    
    tests = [
        ("Basic CLI", run_basic_test),
        ("Authentication", run_auth_test),
        ("Agent Management", run_agent_test)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- Running {test_name} Tests ---")
        if test_func():
            passed += 1
        else:
            failed += 1
    
    print(f"\n--- Test Results ---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    return failed == 0

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)