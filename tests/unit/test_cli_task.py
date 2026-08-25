import json

from miminions.cli.task import load_tasks, save_tasks, task_cli


def test_task_storage_round_trip(tmp_path, monkeypatch):
    monkeypatch.setattr("miminions.cli.task.get_config_dir", lambda: tmp_path)

    loaded_tasks = load_tasks()
    assert loaded_tasks == {}, f"expect load_tasks returns an empty mapping when no task file exists as {{}}, got {loaded_tasks}"
    save_tasks({"t1": {"title": "One"}})

    loaded_tasks = load_tasks()
    assert loaded_tasks == {"t1": {"title": "One"}}, f"expect save_tasks persists task payload and load_tasks returns the stored mapping as {'t1': {'title': 'One'}}, got {loaded_tasks}"


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
    assert added.exit_code == 0, f"expect cli exit code 0, got {added.exit_code} with output: {added.output}"
    assert "Task 'Write tests' added successfully with ID: 12345678" in added.output, f"expect task add command reports created task id for the new task as {"Task 'Write tests' added successfully with ID: 12345678"}, got {added.output}"

    listed = isolated_cli_runner.invoke(task_cli, ["list"])
    assert "12345678: Write tests (pending, high) - Cover CLI" in listed.output, f"expect task list includes the created task with id, status, priority, and description as '12345678: Write tests (pending, high) - Cover CLI', got {listed.output}"

    shown = isolated_cli_runner.invoke(task_cli, ["show", "12345678"])
    assert "Agent: agent1" in shown.output, f"expect task show displays linked agent field for the selected task as 'Agent: agent1', got {shown.output}"

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
    assert updated.exit_code == 0, f"expect cli exit code 0, got {updated.exit_code} with output: {updated.output}"
    assert "updated successfully" in updated.output, f"expect task update command confirms successful task modification as 'updated successfully', got {updated.output}"

    data = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert data["12345678"]["title"] == "Write more tests", f"expect task title is persisted as the updated value after task update command as 'Write more tests', got {data['12345678']['title']}"
    assert data["12345678"]["status"] == "completed", f"expect task status is persisted as completed after task update command as 'completed', got {data['12345678']['status']}"

    removed = isolated_cli_runner.invoke(task_cli, ["remove", "12345678", "--yes"])
    assert removed.exit_code == 0, f"expect cli exit code 0, got {removed.exit_code} with output: {removed.output}"
    assert "removed successfully" in removed.output, f"expect task remove command confirms successful removal as 'removed successfully', got {removed.output}"
    tasks_data = json.loads((tmp_path / "tasks.json").read_text(encoding="utf-8"))
    assert tasks_data == {}, f"expect task store is empty after removing the only task as {{}}, got {tasks_data}"


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
    assert duplicated.exit_code == 0, f"expect cli exit code 0, got {duplicated.exit_code} with output: {duplicated.output}"
    assert "Task duplicated successfully with ID: abcdef12" in duplicated.output, f"expect task duplicate command reports id of the duplicated task as 'Task duplicated successfully with ID: abcdef12', got {duplicated.output}"

    data = load_tasks()
    copied_title = data["abcdef12"]["title"]
    assert copied_title == "Original (copy)", f"expect duplicated task title is suffixed with '(copy)', got {copied_title}"
    assert data["abcdef12"]["status"] == "pending", f"expect duplicated task status resets to pending for new task workflow as 'pending', got {data['abcdef12']['status']}"
    assert data["abcdef12"]["updated_at"] is None, f"expect duplicated task updated_at is cleared for newly created copy as None, got {data['abcdef12']['updated_at']}"

    for command in (
        ["show", "missing"],
        ["update", "missing", "--title", "x"],
        ["duplicate", "missing"],
        ["remove", "missing", "--yes"],
    ):
        result = isolated_cli_runner.invoke(task_cli, command)
        assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
        assert "not found" in result.output, f"expect task command reports missing-task path for unknown task id as 'not found', got {result.output}"


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

    assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
    assert "Invalid value for '--priority'" in result.output, f"expect \"Invalid value for '--priority'\" in result.output, got {result.output}"
