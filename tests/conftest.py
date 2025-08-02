"""
Pytest configuration for MiMinions CLI tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path


@pytest.fixture
def temp_config_dir():
    """Provide a temporary configuration directory for tests."""
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir) / ".miminions"
    config_dir.mkdir(exist_ok=True)
    
    yield config_dir
    
    # Cleanup
    shutil.rmtree(temp_dir, ignore_errors=True)


@pytest.fixture
def isolated_cli_runner():
    """Provide a CLI runner with isolated configuration."""
    from click.testing import CliRunner
    return CliRunner()