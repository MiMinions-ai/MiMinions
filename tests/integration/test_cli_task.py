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

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"
    assert "Agent 'missing' not found." in result.output, f"expect \"Agent 'missing' not found.\" in result.output, got {"Agent 'missing' not found." in result.output}"


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

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"
    assert "Task 'Task A' added successfully" in result.output, f"expect \"Task 'Task A' added successfully\" in result.output, got {"Task 'Task A' added successfully" in result.output}"

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

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"
    assert "Agent 'missing' not found." in result.output, f"expect \"Agent 'missing' not found.\" in result.output, got {"Agent 'missing' not found." in result.output}"

    tasks = _read(temp_config_dir / "tasks.json")
    assert tasks["task1"]["agent"] == "known", f"expect tasks['task1']['agent'] == 'known', got {tasks['task1']['agent'] == 'known'}"


def test_task_list_and_show_json_output():
    runner = CliRunner()
    tasks = {
        "task01": {
            "title": "Write docs",
            "description": "Update CLI docs",
            "priority": "high",
            "status": "pending",
            "agent": "research_agent",
            "created_at": "2026-07-13T00:00:00+00:00",
            "updated_at": None,
        }
    }

    with _patch_auth_enabled():
        with patch("miminions.cli.task.load_tasks", return_value=tasks):
            list_result = runner.invoke(task_cli, ["list", "--json"])
            show_result = runner.invoke(task_cli, ["show", "task01", "--json"])

    assert list_result.exit_code == 0, f"expect list_result.exit_code == 0, got {list_result.exit_code == 0}"
    assert show_result.exit_code == 0, f"expect show_result.exit_code == 0, got {show_result.exit_code == 0}"

    list_payload = json.loads(list_result.output)
    show_payload = json.loads(show_result.output)

    assert list_payload[0]["id"] == "task01", f"expect list_payload[0]['id'] == 'task01', got {list_payload[0]['id'] == 'task01'}"
    assert show_payload["id"] == "task01", f"expect show_payload['id'] == 'task01', got {show_payload['id'] == 'task01'}"
    assert show_payload["title"] == "Write docs", f"expect show_payload['title'] == 'Write docs', got {show_payload['title'] == 'Write docs'}"
