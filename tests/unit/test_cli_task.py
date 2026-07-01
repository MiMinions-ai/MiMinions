import json

from miminions.cli.task import load_tasks, save_tasks, task_cli


def test_task_storage_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.task.get_config_dir", lambda: tmp_path)

    assert load_tasks() == {}
    save_tasks({"t1": {"title": "One"}})

    assert load_tasks() == {"t1": {"title": "One"}}


def test_task_crud_commands_persist_json(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.task.get_config_dir", lambda: tmp_path)
    monkeypatch.setattr("miminions.cli.task.uuid.uuid4", lambda: "12345678-aaaa")

    added = isolated_cli_runner.invoke(
        task_cli,
        [
            "add",
            "--title",
            "Write tests",
            "--description",
            "Cover CLI",
            "--priority",
            "high",
            "--agent",
            "agent1",
        ],
    )
    assert added.exit_code == 0
    assert "Task 'Write tests' added successfully with ID: 12345678" in added.output

    listed = isolated_cli_runner.invoke(task_cli, ["list"])
    assert "12345678: Write tests (pending, high) - Cover CLI" in listed.output

    shown = isolated_cli_runner.invoke(task_cli, ["show", "12345678"])
    assert "Agent: agent1" in shown.output

    updated = isolated_cli_runner.invoke(
        task_cli,
        [
            "update",
            "12345678",
            "--title",
            "Write more tests",
            "--status",
            "completed",
        ],
    )
    assert updated.exit_code == 0
    assert "updated successfully" in updated.output

    data = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert data["12345678"]["title"] == "Write more tests"
    assert data["12345678"]["status"] == "completed"

    removed = isolated_cli_runner.invoke(task_cli, ["remove", "12345678", "--yes"])
    assert removed.exit_code == 0
    assert "removed successfully" in removed.output
    assert json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8")) == {}


def test_task_duplicate_and_missing_paths(isolated_cli_runner, tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)
    monkeypatch.setattr("miminions.cli.task.get_config_dir", lambda: tmp_path)
    save_tasks(
        {
            "task1": {
                "title": "Original",
                "description": "Copy me",
                "priority": "medium",
                "status": "completed",
                "agent": None,
                "created_at": "old",
                "updated_at": "old",
            }
        }
    )
    monkeypatch.setattr("miminions.cli.task.uuid.uuid4", lambda: "abcdef12-bbbb")

    duplicated = isolated_cli_runner.invoke(task_cli, ["duplicate", "task1"])
    assert duplicated.exit_code == 0
    assert "Task duplicated successfully with ID: abcdef12" in duplicated.output

    data = load_tasks()
    assert data["abcdef12"]["title"] == "Original (copy)"
    assert data["abcdef12"]["status"] == "pending"
    assert data["abcdef12"]["updated_at"] is None

    for command in (
        ["show", "missing"],
        ["update", "missing", "--title", "x"],
        ["duplicate", "missing"],
        ["remove", "missing", "--yes"],
    ):
        result = isolated_cli_runner.invoke(task_cli, command)
        assert result.exit_code == 0
        assert "not found" in result.output


def test_task_add_rejects_invalid_priority(isolated_cli_runner, monkeypatch):
    monkeypatch.setattr("miminions.core.auth.is_authenticated", lambda: True)

    result = isolated_cli_runner.invoke(
        task_cli,
        [
            "add",
            "--title",
            "Bad",
            "--description",
            "Bad",
            "--priority",
            "urgent",
        ],
    )

    assert result.exit_code != 0
    assert "Invalid value for '--priority'" in result.output
