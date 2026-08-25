"""
Unit tests for the MiMinions CLI authentication module.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from miminions.cli.auth import (
    auth_cli,
    clear_auth_data,
    get_auth_file,
    get_config_dir,
    is_authenticated,
    load_auth_data,
    save_auth_data,
)


class TestAuthFunctions:
    """Test authentication utility functions."""

    def test_get_config_dir_creates_directory(self):
        """Test that get_config_dir creates the config directory."""
        with patch.dict(os.environ, {}, clear=False) as _env:
            os.environ.pop('MIMINIONS_HOME', None)
            with patch('pathlib.Path.home') as mock_home:
                mock_home.return_value = Path('/tmp/test_home')
                with patch('pathlib.Path.mkdir') as mock_mkdir:
                    config_dir = get_config_dir()
                    expected_path = Path('/tmp/test_home/.miminions')
                    assert config_dir == expected_path, f"expect result to be {expected_path}, got {config_dir}"
                    mock_mkdir.assert_called_once_with(parents=True, exist_ok=True)

    def test_get_config_dir_honors_miminions_home_env(self):
        """MIMINIONS_HOME overrides the default ~/.miminions location."""
        with patch.dict(os.environ, {'MIMINIONS_HOME': '/tmp/custom_home'}):
            with patch('pathlib.Path.mkdir'):
                config_dir = get_config_dir()
                expected_path = Path('/tmp/custom_home')
                assert config_dir == expected_path, f"expect result to be {expected_path}, got {config_dir}"

    def test_get_auth_file(self):
        """Test that get_auth_file returns correct path."""
        with patch('miminions.cli.auth.get_config_dir') as mock_get_config_dir:
            mock_get_config_dir.return_value = Path('/tmp/test_config')
            auth_file = get_auth_file()
            expected_path = Path('/tmp/test_config/auth.json')
            assert auth_file == expected_path, f"expect result to be {expected_path}, got {auth_file}"

    def test_is_authenticated_no_file(self):
        """Test is_authenticated returns False when no auth file exists."""
        with patch('miminions.cli.auth.get_auth_file') as mock_get_auth_file:
            mock_auth_file = MagicMock()
            mock_auth_file.exists.return_value = False
            mock_get_auth_file.return_value = mock_auth_file
            
            is_auth = is_authenticated()
            assert is_auth is False, f"expect result to be {False}, got {is_auth}"

    def test_is_authenticated_empty_file(self):
        """Test is_authenticated returns False for empty auth file."""
        with patch('miminions.cli.auth.get_auth_file') as mock_get_auth_file:
            mock_auth_file = MagicMock()
            mock_auth_file.exists.return_value = True
            mock_stat = MagicMock()
            mock_stat.st_size = 0
            mock_auth_file.stat.return_value = mock_stat
            mock_get_auth_file.return_value = mock_auth_file
            
            is_auth = is_authenticated()
            assert is_auth is False, f"expect result to be {False}, got {is_auth}"

    def test_is_authenticated_valid_file(self):
        """Test is_authenticated returns True for valid auth file."""
        with patch('miminions.cli.auth.get_auth_file') as mock_get_auth_file:
            mock_auth_file = MagicMock()
            mock_auth_file.exists.return_value = True
            mock_stat = MagicMock()
            mock_stat.st_size = 100
            mock_auth_file.stat.return_value = mock_stat
            mock_get_auth_file.return_value = mock_auth_file
            
            is_auth = is_authenticated()
            assert is_auth is True, f"expect result to be {True}, got {is_auth}"

    def test_save_auth_data(self):
        """Test save_auth_data writes data to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with patch('miminions.cli.auth.get_auth_file') as mock_get_auth_file:
                mock_get_auth_file.return_value = Path(tmp_path)
                
                test_data = {"username": "testuser", "authenticated": True}
                save_auth_data(test_data)
                
                with open(tmp_path, 'r') as f:
                    saved_data = json.load(f)
                
                assert saved_data == test_data, f"expect result to be {test_data}, got {saved_data}"
        finally:
            os.unlink(tmp_path)

    def test_load_auth_data_no_file(self):
        """Test load_auth_data returns None when no file exists."""
        with patch('miminions.cli.auth.get_auth_file') as mock_get_auth_file:
            mock_auth_file = MagicMock()
            mock_auth_file.exists.return_value = False
            mock_get_auth_file.return_value = mock_auth_file
            
            loaded_data = load_auth_data()
            assert loaded_data is None, f"expect result to be {None}, got {loaded_data}"

    def test_load_auth_data_valid_file(self):
        """Test load_auth_data returns data from file."""
        test_data = {"username": "testuser", "authenticated": True}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            json.dump(test_data, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            with patch('miminions.cli.auth.get_auth_file') as mock_get_auth_file:
                mock_get_auth_file.return_value = Path(tmp_path)
                
                loaded_data = load_auth_data()
                assert loaded_data == test_data, f"expect result to be {test_data}, got {loaded_data}"
        finally:
            os.unlink(tmp_path)

    def test_clear_auth_data(self):
        """Test clear_auth_data removes auth file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with patch('miminions.cli.auth.get_auth_file') as mock_get_auth_file:
                mock_get_auth_file.return_value = Path(tmp_path)
                
                # Verify file exists
                auth_file_exists_before_clear = os.path.exists(tmp_path)
                assert auth_file_exists_before_clear, f"expect auth file exists before clear_auth_data runs as True, got {auth_file_exists_before_clear}"
                
                clear_auth_data()
                
                # Verify file is removed
                auth_file_exists_after_clear = os.path.exists(tmp_path)
                assert not auth_file_exists_after_clear, f"expect auth file removed by clear_auth_data as False, got {auth_file_exists_after_clear}"
        except FileNotFoundError:
            # File already removed, which is expected
            pass


class TestAuthCLI:
    """Test authentication CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_signin_success(self):
        """Test successful signin."""
        with patch('miminions.cli.auth.save_auth_data') as mock_save:
            result = self.runner.invoke(auth_cli, ['signin', '--username', 'testuser', '--password', 'testpass'])
            
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert 'Successfully signed in as testuser' in result.output, f"expect signin command confirms successful authentication for provided username as 'Successfully signed in as testuser', got {result.output}"
            mock_save.assert_called_once()

    def test_signin_missing_username(self):
        """Test signin with missing username."""
        result = self.runner.invoke(auth_cli, ['signin', '--password', 'testpass'])
        
        assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"

    def test_signin_missing_password(self):
        """Test signin with missing password."""
        result = self.runner.invoke(auth_cli, ['signin', '--username', 'testuser'])
        
        assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"

    def test_signout_authenticated(self):
        """Test signout when authenticated."""
        with patch('miminions.cli.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.auth.load_auth_data') as mock_load:
                with patch('miminions.cli.auth.clear_auth_data') as mock_clear:
                    mock_is_auth.return_value = True
                    mock_load.return_value = {"username": "testuser"}
                    
                    result = self.runner.invoke(auth_cli, ['signout'])
                    
                    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                    assert 'Successfully signed out testuser' in result.output, f"expect signout command confirms signed-out username when credentials exist as 'Successfully signed out testuser', got {result.output}"
                    mock_clear.assert_called_once()

    def test_signout_not_authenticated(self):
        """Test signout when not authenticated."""
        with patch('miminions.cli.auth.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            
            result = self.runner.invoke(auth_cli, ['signout'])
            
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert 'You are not currently signed in' in result.output, f"expect signout command reports no active authentication when user is already signed out as 'You are not currently signed in', got {result.output}"

    def test_status_authenticated(self):
        """Test status when authenticated."""
        with patch('miminions.cli.auth.is_authenticated') as mock_is_auth:
            with patch('miminions.cli.auth.load_auth_data') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {"username": "testuser"}
                
                result = self.runner.invoke(auth_cli, ['status'])
                
                assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
                assert 'Signed in as: testuser' in result.output, f"expect status command reports active signed-in username from auth data as 'Signed in as: testuser', got {result.output}"

    def test_status_not_authenticated(self):
        """Test status when not authenticated."""
        with patch('miminions.cli.auth.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            
            result = self.runner.invoke(auth_cli, ['status'])
            
            assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
            assert 'Not signed in' in result.output, f"expect status command reports not-signed-in state when authentication is absent as 'Not signed in', got {result.output}"
