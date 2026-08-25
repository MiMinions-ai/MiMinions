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

    assert config["default_workspace"], f"expect truthy value, got {config['default_workspace']}"
    assert config["default_agent"] == "default", f"expect 'default', got {config['default_agent']}"

    saved = json.loads((temp_config_dir / "config.json").read_text())
    assert saved == config, f"expect config, got {saved}"

    root = _workspace_root(temp_config_dir, config)
    assert (root / "prompt" / "AGENTS.md").exists(), f"expect truthy value, got {(root / 'prompt' / 'AGENTS.md').exists()}"
    assert (root / "prompt" / "USER.md").exists(), f"expect truthy value, got {(root / 'prompt' / 'USER.md').exists()}"
    assert (root / "prompt" / "TOOLS.md").exists(), f"expect truthy value, got {(root / 'prompt' / 'TOOLS.md').exists()}"
    assert (root / "prompt" / "IDENTITY.md").exists(), f"expect truthy value, got {(root / 'prompt' / 'IDENTITY.md').exists()}"
    assert (root / "skills" / "core" / "SKILL.md").exists(), f"expect truthy value, got {(root / 'skills' / 'core' / 'SKILL.md').exists()}"
    assert (root / "memory" / "MEMORY.md").exists(), f"expect truthy value, got {(root / 'memory' / 'MEMORY.md').exists()}"
    assert (root / "sessions").is_dir(), f"expect truthy value, got {(root / 'sessions').is_dir()}"
    assert (root / "data").is_dir(), f"expect truthy value, got {(root / 'data').is_dir()}"

    agents = json.loads((temp_config_dir / "agents.json").read_text())
    assert agents["default"]["base_agent"] == "miminions.agent.Minion", f"expect 'miminions.agent.Minion', got {agents['default']['base_agent']}"

    workspaces = json.loads((temp_config_dir / "workspaces.json").read_text())
    assert config["default_workspace"] in workspaces, f"expect contains config['default_workspace'], got {workspaces}"
    assert workspaces[config["default_workspace"]]["name"] == "default", f"expect 'default', got {workspaces[config['default_workspace']]['name']}"


def test_second_run_is_noop(temp_config_dir):
    first = ensure_default_setup(temp_config_dir)

    user_md = _workspace_root(temp_config_dir, first) / "prompt" / "USER.md"
    user_md.write_text("# customized by user\n")

    second = ensure_default_setup(temp_config_dir)

    assert second == first, f"expect first, got {second}"
    assert user_md.read_text() == "# customized by user\n", f"expect '# customized by user\\n', got {user_md.read_text()}"


def test_corrupt_config_raises(temp_config_dir):
    (temp_config_dir / "config.json").write_text("{ not valid json")

    with pytest.raises(ValueError):
        ensure_default_setup(temp_config_dir)


def test_existing_agents_are_preserved(temp_config_dir):
    agents_file = temp_config_dir / "agents.json"
    agents_file.write_text(json.dumps({"mybot": {"name": "mybot"}}))

    config = ensure_default_setup(temp_config_dir)

    assert config["default_agent"] == "mybot", f"expect 'mybot', got {config['default_agent']}"
    agents = json.loads(agents_file.read_text())
    assert list(agents) == ["mybot"], f"expect ['mybot'], got {list(agents)}"


def test_force_repairs_missing_templates_without_overwrite(temp_config_dir):
    config = ensure_default_setup(temp_config_dir)
    root = _workspace_root(temp_config_dir, config)

    tools_md = root / "prompt" / "TOOLS.md"
    user_md = root / "prompt" / "USER.md"
    user_md.write_text("# customized by user\n")
    tools_md.unlink()

    ensure_default_setup(temp_config_dir, force=True)

    assert tools_md.exists(), f"expect truthy value, got {tools_md.exists()}"
    assert user_md.read_text() == "# customized by user\n", f"expect '# customized by user\\n', got {user_md.read_text()}"
