"""
Pytest configuration for MiMinions CLI tests.
"""

import os
import sys
import pytest
import tempfile
import shutil
from pathlib import Path

# Provide placeholder credentials so model clients (OpenAI/OpenRouter/etc.)
# can be constructed during tests without real secrets. Newer openai SDKs
# reject empty api keys at client construction; tests never make live calls.
for _key in ("OPENROUTER_API_KEY", "OPENAI_API_KEY", "ANTHROPIC_API_KEY", "GEMINI_API_KEY"):
    os.environ.setdefault(_key, "test-placeholder")

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"

if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

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