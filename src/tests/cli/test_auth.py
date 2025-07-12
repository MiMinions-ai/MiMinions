"""
Unit tests for the MiMinions CLI authentication module.
"""

import pytest
import json
import tempfile
import os
from pathlib import Path
from unittest.mock import patch, MagicMock
from click.testing import CliRunner

from interface.cli.auth import auth_cli, get_config_dir, get_auth_file, is_authenticated, save_auth_data, load_auth_data, clear_auth_data


class TestAuthFunctions:
    """Test authentication utility functions."""

    def test_get_config_dir_creates_directory(self):
        """Test that get_config_dir creates the config directory."""
        with patch('pathlib.Path.home') as mock_home:
            mock_home.return_value = Path('/tmp/test_home')
            with patch('pathlib.Path.mkdir') as mock_mkdir:
                config_dir = get_config_dir()
                assert config_dir == Path('/tmp/test_home/.miminions')
                mock_mkdir.assert_called_once_with(exist_ok=True)

    def test_get_auth_file(self):
        """Test that get_auth_file returns correct path."""
        with patch('interface.cli.auth.get_config_dir') as mock_get_config_dir:
            mock_get_config_dir.return_value = Path('/tmp/test_config')
            auth_file = get_auth_file()
            assert auth_file == Path('/tmp/test_config/auth.json')

    def test_is_authenticated_no_file(self):
        """Test is_authenticated returns False when no auth file exists."""
        with patch('interface.cli.auth.get_auth_file') as mock_get_auth_file:
            mock_auth_file = MagicMock()
            mock_auth_file.exists.return_value = False
            mock_get_auth_file.return_value = mock_auth_file
            
            assert is_authenticated() is False

    def test_is_authenticated_empty_file(self):
        """Test is_authenticated returns False for empty auth file."""
        with patch('interface.cli.auth.get_auth_file') as mock_get_auth_file:
            mock_auth_file = MagicMock()
            mock_auth_file.exists.return_value = True
            mock_stat = MagicMock()
            mock_stat.st_size = 0
            mock_auth_file.stat.return_value = mock_stat
            mock_get_auth_file.return_value = mock_auth_file
            
            assert is_authenticated() is False

    def test_is_authenticated_valid_file(self):
        """Test is_authenticated returns True for valid auth file."""
        with patch('interface.cli.auth.get_auth_file') as mock_get_auth_file:
            mock_auth_file = MagicMock()
            mock_auth_file.exists.return_value = True
            mock_stat = MagicMock()
            mock_stat.st_size = 100
            mock_auth_file.stat.return_value = mock_stat
            mock_get_auth_file.return_value = mock_auth_file
            
            assert is_authenticated() is True

    def test_save_auth_data(self):
        """Test save_auth_data writes data to file."""
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with patch('interface.cli.auth.get_auth_file') as mock_get_auth_file:
                mock_get_auth_file.return_value = Path(tmp_path)
                
                test_data = {"username": "testuser", "authenticated": True}
                save_auth_data(test_data)
                
                with open(tmp_path, 'r') as f:
                    saved_data = json.load(f)
                
                assert saved_data == test_data
        finally:
            os.unlink(tmp_path)

    def test_load_auth_data_no_file(self):
        """Test load_auth_data returns None when no file exists."""
        with patch('interface.cli.auth.get_auth_file') as mock_get_auth_file:
            mock_auth_file = MagicMock()
            mock_auth_file.exists.return_value = False
            mock_get_auth_file.return_value = mock_auth_file
            
            assert load_auth_data() is None

    def test_load_auth_data_valid_file(self):
        """Test load_auth_data returns data from file."""
        test_data = {"username": "testuser", "authenticated": True}
        
        with tempfile.NamedTemporaryFile(mode='w', delete=False) as tmp_file:
            json.dump(test_data, tmp_file)
            tmp_path = tmp_file.name
        
        try:
            with patch('interface.cli.auth.get_auth_file') as mock_get_auth_file:
                mock_get_auth_file.return_value = Path(tmp_path)
                
                loaded_data = load_auth_data()
                assert loaded_data == test_data
        finally:
            os.unlink(tmp_path)

    def test_clear_auth_data(self):
        """Test clear_auth_data removes auth file."""
        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
            tmp_path = tmp_file.name
        
        try:
            with patch('interface.cli.auth.get_auth_file') as mock_get_auth_file:
                mock_get_auth_file.return_value = Path(tmp_path)
                
                # Verify file exists
                assert os.path.exists(tmp_path)
                
                clear_auth_data()
                
                # Verify file is removed
                assert not os.path.exists(tmp_path)
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
        with patch('interface.cli.auth.save_auth_data') as mock_save:
            result = self.runner.invoke(auth_cli, ['signin', '--username', 'testuser', '--password', 'testpass'])
            
            assert result.exit_code == 0
            assert 'Successfully signed in as testuser' in result.output
            mock_save.assert_called_once()

    def test_signin_missing_username(self):
        """Test signin with missing username."""
        result = self.runner.invoke(auth_cli, ['signin', '--password', 'testpass'])
        
        assert result.exit_code != 0

    def test_signin_missing_password(self):
        """Test signin with missing password."""
        result = self.runner.invoke(auth_cli, ['signin', '--username', 'testuser'])
        
        assert result.exit_code != 0

    def test_signout_authenticated(self):
        """Test signout when authenticated."""
        with patch('interface.cli.auth.is_authenticated') as mock_is_auth:
            with patch('interface.cli.auth.load_auth_data') as mock_load:
                with patch('interface.cli.auth.clear_auth_data') as mock_clear:
                    mock_is_auth.return_value = True
                    mock_load.return_value = {"username": "testuser"}
                    
                    result = self.runner.invoke(auth_cli, ['signout'])
                    
                    assert result.exit_code == 0
                    assert 'Successfully signed out testuser' in result.output
                    mock_clear.assert_called_once()

    def test_signout_not_authenticated(self):
        """Test signout when not authenticated."""
        with patch('interface.cli.auth.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            
            result = self.runner.invoke(auth_cli, ['signout'])
            
            assert result.exit_code == 0
            assert 'You are not currently signed in' in result.output

    def test_status_authenticated(self):
        """Test status when authenticated."""
        with patch('interface.cli.auth.is_authenticated') as mock_is_auth:
            with patch('interface.cli.auth.load_auth_data') as mock_load:
                mock_is_auth.return_value = True
                mock_load.return_value = {"username": "testuser"}
                
                result = self.runner.invoke(auth_cli, ['status'])
                
                assert result.exit_code == 0
                assert 'Signed in as: testuser' in result.output

    def test_status_not_authenticated(self):
        """Test status when not authenticated."""
        with patch('interface.cli.auth.is_authenticated') as mock_is_auth:
            mock_is_auth.return_value = False
            
            result = self.runner.invoke(auth_cli, ['status'])
            
            assert result.exit_code == 0
            assert 'Not signed in' in result.output