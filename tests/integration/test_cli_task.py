"""Integration tests for task CLI behavior."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from miminions.cli.task import task_cli


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _patch_auth_enabled():
    return patch("miminions.core.auth.is_authenticated", return_value=True)


def test_task_add_rejects_unknown_agent(temp_config_dir):
    runner = CliRunner()
    _write(temp_config_dir / "agents.json", {"known": {"name": "Known"}})

    with _patch_auth_enabled():
        with patch("miminions.cli.task.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(
                task_cli,
                [
                    "add",
                    "--title",
                    "Task A",
                    "--description",
                    "Desc",
                    "--priority",
                    "medium",
                    "--agent",
                    "missing",
                ],
            )

    assert result.exit_code == 0
    assert "Agent 'missing' not found." in result.output


def test_task_add_accepts_existing_agent(temp_config_dir):
    runner = CliRunner()
    _write(temp_config_dir / "agents.json", {"known": {"name": "Known"}})

    with _patch_auth_enabled():
        with patch("miminions.cli.task.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(
                task_cli,
                [
                    "add",
                    "--title",
                    "Task A",
                    "--description",
                    "Desc",
                    "--priority",
                    "medium",
                    "--agent",
                    "known",
                ],
            )

    assert result.exit_code == 0
    assert "added successfully" in result.output


def test_task_update_rejects_unknown_agent(temp_config_dir):
    runner = CliRunner()
    _write(temp_config_dir / "agents.json", {"known": {"name": "Known"}})
    _write(
        temp_config_dir / "tasks.json",
        {
            "task1": {
                "title": "Task 1",
                "description": "Desc",
                "priority": "medium",
                "status": "pending",
                "agent": "known",
                "created_at": "",
                "updated_at": None,
            }
        },
    )

    with _patch_auth_enabled():
        with patch("miminions.cli.task.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(task_cli, ["update", "task1", "--agent", "missing"])

    assert result.exit_code == 0
    assert "Agent 'missing' not found." in result.output

    tasks = _read(temp_config_dir / "tasks.json")
    assert tasks["task1"]["agent"] == "known"
