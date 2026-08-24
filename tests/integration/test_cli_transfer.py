"""Integration tests for top-level export/import commands."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from miminions.cli.main import cli


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def test_export_writes_agents_tasks_knowledge(temp_config_dir, tmp_path):
    runner = CliRunner()

    _write(temp_config_dir / "agents.json", {"a1": {"name": "Agent One"}})
    _write(temp_config_dir / "tasks.json", {"t1": {"title": "Task One"}})
    _write(temp_config_dir / "knowledge.json", {"k1": {"title": "Knowledge One"}})

    out = tmp_path / "backup.json"

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.transfer.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["export", "--output", str(out)])

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"
    assert out.exists(), f"expect out.exists(), got {out.exists()}"

    payload = _read(out)
    assert payload["version"] == 1, f"expect payload['version'] == 1, got {payload['version'] == 1}"
    assert payload["agents"]["a1"]["name"] == "Agent One", f"expect payload['agents']['a1']['name'] == 'Agent One', got {payload['agents']['a1']['name'] == 'Agent One'}"
    assert payload["tasks"]["t1"]["title"] == "Task One", f"expect payload['tasks']['t1']['title'] == 'Task One', got {payload['tasks']['t1']['title'] == 'Task One'}"
    assert payload["knowledge"]["k1"]["title"] == "Knowledge One", f"expect payload['knowledge']['k1']['title'] == 'Knowledge One', got {payload['knowledge']['k1']['title'] == 'Knowledge One'}"


def test_import_merge_adds_records(temp_config_dir, tmp_path):
    runner = CliRunner()

    _write(temp_config_dir / "agents.json", {"existing": {"name": "Existing"}})
    _write(temp_config_dir / "tasks.json", {})
    _write(temp_config_dir / "knowledge.json", {})

    backup = tmp_path / "backup.json"
    _write(
        backup,
        {
            "version": 1,
            "agents": {"new": {"name": "New Agent"}},
            "tasks": {"t1": {"title": "Task One"}},
            "knowledge": {"k1": {"title": "Knowledge One"}},
        },
    )

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.transfer.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["import", "--input", str(backup), "--mode", "merge"])

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"

    agents = _read(temp_config_dir / "agents.json")
    tasks = _read(temp_config_dir / "tasks.json")
    knowledge = _read(temp_config_dir / "knowledge.json")

    assert "existing" in agents, f"expect 'existing' in agents, got {'existing' in agents}"
    assert "new" in agents, f"expect 'new' in agents, got {'new' in agents}"
    assert "t1" in tasks, f"expect 't1' in tasks, got {'t1' in tasks}"
    assert "k1" in knowledge, f"expect 'k1' in knowledge, got {'k1' in knowledge}"


def test_import_replace_overwrites_records(temp_config_dir, tmp_path):
    runner = CliRunner()

    _write(temp_config_dir / "agents.json", {"existing": {"name": "Existing"}})
    _write(temp_config_dir / "tasks.json", {"old": {"title": "Old Task"}})
    _write(temp_config_dir / "knowledge.json", {"old": {"title": "Old Knowledge"}})

    backup = tmp_path / "backup.json"
    _write(
        backup,
        {
            "version": 1,
            "agents": {"new": {"name": "New Agent"}},
            "tasks": {"t1": {"title": "Task One"}},
            "knowledge": {"k1": {"title": "Knowledge One"}},
        },
    )

    with patch("miminions.cli.main.get_config_dir", return_value=temp_config_dir):
        with patch("miminions.cli.transfer.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(cli, ["import", "--input", str(backup), "--mode", "replace"])

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"

    agents = _read(temp_config_dir / "agents.json")
    tasks = _read(temp_config_dir / "tasks.json")
    knowledge = _read(temp_config_dir / "knowledge.json")

    assert "existing" not in agents, f"expect 'existing' not in agents, got {'existing' not in agents}"
    assert "old" not in tasks, f"expect 'old' not in tasks, got {'old' not in tasks}"
    assert "old" not in knowledge, f"expect 'old' not in knowledge, got {'old' not in knowledge}"

    assert "new" in agents, f"expect 'new' in agents, got {'new' in agents}"
    assert "t1" in tasks, f"expect 't1' in tasks, got {'t1' in tasks}"
    assert "k1" in knowledge, f"expect 'k1' in knowledge, got {'k1' in knowledge}"
