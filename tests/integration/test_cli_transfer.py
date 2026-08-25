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

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    output_file_exists = out.exists()
    assert output_file_exists, f"expect export command creates output backup file, got {output_file_exists}"

    payload = _read(out)
    assert payload["version"] == 1, f"expect result to be {1}, got {payload['version']}"
    assert payload["agents"]["a1"]["name"] == "Agent One", f"expect result to be {'Agent One'}, got {payload['agents']['a1']['name']}"
    assert payload["tasks"]["t1"]["title"] == "Task One", f"expect result to be {'Task One'}, got {payload['tasks']['t1']['title']}"
    assert payload["knowledge"]["k1"]["title"] == "Knowledge One", f"expect result to be {'Knowledge One'}, got {payload['knowledge']['k1']['title']}"


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

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"

    agents = _read(temp_config_dir / "agents.json")
    tasks = _read(temp_config_dir / "tasks.json")
    knowledge = _read(temp_config_dir / "knowledge.json")

    assert "existing" in agents, f"expect import --mode merge preserves existing agent key 'existing', got {agents}"
    assert "new" in agents, f"expect import --mode merge adds backup agent key 'new', got {agents}"
    assert "t1" in tasks, f"expect import --mode merge adds backup task key 't1', got {tasks}"
    assert "k1" in knowledge, f"expect import --mode merge adds backup knowledge key 'k1', got {knowledge}"


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

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"

    agents = _read(temp_config_dir / "agents.json")
    tasks = _read(temp_config_dir / "tasks.json")
    knowledge = _read(temp_config_dir / "knowledge.json")

    assert "existing" not in agents, f"expect import --mode replace removes pre-existing agent key 'existing', got {agents}"
    assert "old" not in tasks, f"expect import --mode replace removes pre-existing task key 'old', got {tasks}"
    assert "old" not in knowledge, f"expect import --mode replace removes pre-existing knowledge key 'old', got {knowledge}"

    assert "new" in agents, f"expect import --mode replace writes backup agent key 'new', got {agents}"
    assert "t1" in tasks, f"expect import --mode replace writes backup task key 't1', got {tasks}"
    assert "k1" in knowledge, f"expect import --mode replace writes backup knowledge key 'k1', got {knowledge}"
