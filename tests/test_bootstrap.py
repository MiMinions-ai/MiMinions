"""
Tests for the first-run default setup bootstrap.
"""

import json

import pytest

from miminions.core.bootstrap import ensure_default_setup


def _workspace_root(config_dir, config):
    return config_dir / "workspaces" / f"ws_{config['default_workspace']}"


def test_first_run_creates_defaults(temp_config_dir):
    config = ensure_default_setup(temp_config_dir)

    assert config["default_workspace"]
    assert config["default_agent"] == "default"

    saved = json.loads((temp_config_dir / "config.json").read_text())
    assert saved == config

    root = _workspace_root(temp_config_dir, config)
    assert (root / "prompt" / "AGENTS.md").exists()
    assert (root / "prompt" / "USER.md").exists()
    assert (root / "prompt" / "TOOLS.md").exists()
    assert (root / "prompt" / "IDENTITY.md").exists()
    assert (root / "skills" / "core" / "SKILL.md").exists()
    assert (root / "memory" / "MEMORY.md").exists()
    assert (root / "sessions").is_dir()
    assert (root / "data").is_dir()

    agents = json.loads((temp_config_dir / "agents.json").read_text())
    assert agents["default"]["base_agent"] == "miminions.agent.Minion"

    workspaces = json.loads((temp_config_dir / "workspaces.json").read_text())
    assert config["default_workspace"] in workspaces
    assert workspaces[config["default_workspace"]]["name"] == "default"


def test_second_run_is_noop(temp_config_dir):
    first = ensure_default_setup(temp_config_dir)

    user_md = _workspace_root(temp_config_dir, first) / "prompt" / "USER.md"
    user_md.write_text("# customized by user\n")

    second = ensure_default_setup(temp_config_dir)

    assert second == first
    assert user_md.read_text() == "# customized by user\n"


def test_corrupt_config_raises(temp_config_dir):
    (temp_config_dir / "config.json").write_text("{ not valid json")

    with pytest.raises(ValueError):
        ensure_default_setup(temp_config_dir)


def test_existing_agents_are_preserved(temp_config_dir):
    agents_file = temp_config_dir / "agents.json"
    agents_file.write_text(json.dumps({"mybot": {"name": "mybot"}}))

    config = ensure_default_setup(temp_config_dir)

    assert config["default_agent"] == "mybot"
    agents = json.loads(agents_file.read_text())
    assert list(agents) == ["mybot"]
