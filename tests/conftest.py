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


@pytest.fixture
def temp_db_path(tmp_path):
    """Provide a temporary database path."""
    return tmp_path / "test.db"


# Pytest markers
def pytest_configure(config):
    """Register custom markers."""
    config.addinivalue_line(
        "markers", "slow: marks tests as slow (deselect with '-m \"not slow\"')"
    )
    config.addinivalue_line(
        "markers", "integration: marks tests as integration tests"
    )
    config.addinivalue_line(
        "markers", "unit: marks tests as unit tests"
    )
    config.addinivalue_line(
        "markers", "stress: marks tests as stress tests"
    )