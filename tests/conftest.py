"""
Pytest configuration for MiMinions CLI tests.
"""

import json
import os
import shutil
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path

import pytest

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


@pytest.fixture(autouse=True)
def _isolated_miminions_home(monkeypatch, tmp_path):
    """Keep tests from reading or writing the developer's real ~/.miminions."""
    monkeypatch.setenv("MIMINIONS_HOME", str(tmp_path / ".miminions-home"))


@pytest.fixture(autouse=True)
def _dummy_openrouter_key(monkeypatch):
    """Keep the suite hermetic.

    The default agent provider ("openrouter") now fails fast when
    OPENROUTER_API_KEY is unset, so non-LLM tests that merely construct a
    Minion would break in CI (bare `pytest`, no secret). Inject a dummy key
    when no real one is present; tests that assert the fail-fast behavior
    delete it again via their own monkeypatch.
    """
    if not os.environ.get("OPENROUTER_API_KEY"):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-dummy-key")


@pytest.fixture
def cli_config_dir(tmp_path):
    """Unique local-first CLI config directory for a test."""
    config_dir = tmp_path / ".miminions"
    config_dir.mkdir(exist_ok=True)
    return config_dir


@pytest.fixture
def authenticated_cli_config_dir(cli_config_dir):
    """Config dir with placeholder auth data for future auth-gated tests."""
    auth_file = cli_config_dir / "auth.json"
    auth_file.write_text(
        json.dumps({"username": "testuser", "authenticated": True}),
        encoding="utf-8",
    )
    return cli_config_dir


@pytest.fixture
def patched_cli_config_dir(monkeypatch):
    """Patch common CLI config-dir lookup points to one test directory."""
    targets = (
        "miminions.core.paths.get_config_dir",
        "miminions.cli.auth.get_config_dir",
        "miminions.cli.config.get_config_dir",
        "miminions.cli.agent.get_config_dir",
        "miminions.cli.chat.get_config_dir",
        "miminions.cli.execution.get_config_dir",
        "miminions.cli.knowledge.get_config_dir",
        "miminions.cli.prompt.get_config_dir",
        "miminions.cli.task.get_config_dir",
        "miminions.cli.transfer.get_config_dir",
        "miminions.cli.workflow.get_config_dir",
        "miminions.cli.workspace.get_config_dir",
    )

    @contextmanager
    def _patch(config_dir: Path):
        for target in targets:
            monkeypatch.setattr(
                target,
                lambda config_dir=config_dir: config_dir,
                raising=False,
            )
        yield config_dir

    return _patch

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