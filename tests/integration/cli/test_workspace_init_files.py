from pathlib import Path

from click.testing import CliRunner

from miminions.cli.workspace import workspace_cli


def test_workspace_add_with_init_files_creates_root_path_and_files(tmp_path, monkeypatch):
    
    monkeypatch.setattr(
        "miminions.core.auth.is_authenticated",
        lambda: True,
    )

    monkeypatch.setattr(
        "miminions.cli.workspace.get_config_dir",
        lambda: tmp_path,
    )

    runner = CliRunner()
    result = runner.invoke(
        workspace_cli,
        [
            "add",
            "--name",
            "phase6-test",
            "--description",
            "phase 6 test workspace",
            "--init-files",
        ],
    )
    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"

    config_dir = tmp_path
    workspaces_file = config_dir / "workspaces.json"
    workspaces_file_exists = workspaces_file.exists()
    assert workspaces_file_exists, f"expect workspace add writes workspaces.json as True, got {workspaces_file_exists}"

    import json
    data = json.loads(workspaces_file.read_text(encoding="utf-8"))
    workspace_count = len(data)
    assert workspace_count == 1, f"expect result to be {1}, got {workspace_count}"

    _workspace_id, workspace_data = next(iter(data.items()))
    assert workspace_data["name"] == "phase6-test", f"expect result to be {'phase6-test'}, got {workspace_data['name']}"
    assert workspace_data["root_path"] is not None, f"expect workspace_data['root_path'] is not None, got {workspace_data['root_path']}"

    root = Path(workspace_data["root_path"])
    root_exists = root.exists()
    assert root_exists, f"expect init-files creates workspace root path as True, got {root_exists}"
    agents_file_exists = (root / "prompt" / "AGENTS.md").exists()
    assert agents_file_exists, f"expect init-files creates prompt/AGENTS.md as True, got {agents_file_exists}"
    memory_file_exists = (root / "memory" / "MEMORY.md").exists()
    assert memory_file_exists, f"expect init-files creates memory/MEMORY.md as True, got {memory_file_exists}"
    sessions_dir_exists = (root / "sessions").exists()
    assert sessions_dir_exists, f"expect init-files creates sessions directory as True, got {sessions_dir_exists}"


def test_workspace_init_files_sets_root_path_for_existing_workspace(tmp_path, monkeypatch):
    
    monkeypatch.setattr(
        "miminions.core.auth.is_authenticated",
        lambda: True,
    )   
    
    monkeypatch.setattr(
        "miminions.cli.workspace.get_config_dir",
        lambda: tmp_path,
    )

    runner = CliRunner()

    add_result = runner.invoke(
        workspace_cli,
        [
            "add",
            "--name",
            "existing-ws",
            "--description",
            "existing workspace",
        ],
    )
    assert add_result.exit_code == 0, f"expect cli exit code 0, got {add_result.exit_code} with output: {add_result.output}"

    init_result = runner.invoke(
        workspace_cli,
        [
            "init-files",
            "existing-ws",
        ],
    )
    assert init_result.exit_code == 0, f"expect cli exit code 0, got {init_result.exit_code} with output: {init_result.output}"

    import json
    workspaces_file = tmp_path / "workspaces.json"
    data = json.loads(workspaces_file.read_text(encoding="utf-8"))
    workspace_count = len(data)
    assert workspace_count == 1, f"expect result to be {1}, got {workspace_count}"

    workspace_id, workspace_data = next(iter(data.items()))
    assert workspace_data["root_path"] is not None, f"expect workspace_data['root_path'] is not None, got {workspace_data['root_path']}"

    root = Path(workspace_data["root_path"])
    root_exists = root.exists()
    assert root_exists, f"expect init-files creates workspace root path for existing workspace as True, got {root_exists}"
    assert root.name == f"ws_{workspace_id}", f"expect result to be {f'ws_{workspace_id}'}, got {root.name}"
    agents_file_exists = (root / "prompt" / "AGENTS.md").exists()
    assert agents_file_exists, f"expect init-files creates prompt/AGENTS.md for existing workspace as True, got {agents_file_exists}"
    memory_file_exists = (root / "memory" / "MEMORY.md").exists()
    assert memory_file_exists, f"expect init-files creates memory/MEMORY.md for existing workspace as True, got {memory_file_exists}"
    sessions_dir_exists = (root / "sessions").exists()
    assert sessions_dir_exists, f"expect init-files creates sessions directory for existing workspace as True, got {sessions_dir_exists}"
