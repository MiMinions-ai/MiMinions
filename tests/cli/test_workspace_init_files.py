from pathlib import Path
from click.testing import CliRunner

from miminions.interface.cli.workspace import workspace_cli


def test_workspace_add_with_init_files_creates_root_path_and_files(tmp_path, monkeypatch):
    
    monkeypatch.setattr(
        "miminions.interface.cli.workspace.is_authenticated",
        lambda: True,
    )

    monkeypatch.setattr(
        "miminions.interface.cli.workspace.get_config_dir",
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
    assert result.exit_code == 0, f"Expected exit code 0, but got {result.exit_code}"

    config_dir = tmp_path
    workspaces_file = config_dir / "workspaces.json"
    assert workspaces_file.exists(), f"Expected file 'workspaces.json' to exist at {workspaces_file}, but it does not."

    import json
    data = json.loads(workspaces_file.read_text(encoding="utf-8"))
    assert len(data) == 1, f"Expected 1 workspace entry, but found {len(data)}"

    workspace_id, workspace_data = next(iter(data.items()))
    assert workspace_data["name"] == "phase6-test", f"Expected workspace name 'phase6-test', but got {workspace_data['name']}"
    assert workspace_data["root_path"] is not None, "Expected a non-None 'root_path', but it was None"

    root = Path(workspace_data["root_path"])
    assert root.exists(), f"Expected root path '{root}' to exist, but it does not."
    assert (root / "prompt" / "AGENTS.md").exists(), "Expected 'AGENTS.md' in the prompt folder, but it was missing."
    assert (root / "memory" / "MEMORY.md").exists(), "Expected 'MEMORY.md' in the memory folder, but it was missing."
    assert (root / "sessions").exists(), "Expected a 'sessions' folder in the root directory, but it was not found."


def test_workspace_init_files_sets_root_path_for_existing_workspace(tmp_path, monkeypatch):
    
    monkeypatch.setattr(
        "miminions.interface.cli.workspace.is_authenticated",
        lambda: True,
    )   
    
    monkeypatch.setattr(
        "miminions.interface.cli.workspace.get_config_dir",
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
    assert add_result.exit_code == 0, f"Expected exit code 0 for adding workspace, but got {add_result.exit_code}"

    init_result = runner.invoke(
        workspace_cli,
        [
            "init-files",
            "existing-ws",
        ],
    )
    assert init_result.exit_code == 0, f"Expected exit code 0 for initializing files, but got {init_result.exit_code}"

    import json
    workspaces_file = tmp_path / "workspaces.json"
    data = json.loads(workspaces_file.read_text(encoding="utf-8"))
    assert len(data) == 1, f"Expected 1 workspace entry, but found {len(data)}"

    workspace_id, workspace_data = next(iter(data.items()))
    assert workspace_data["root_path"] is not None, "Expected 'root_path' to be set, but it was None"

    root = Path(workspace_data["root_path"])
    assert root.exists(), f"Expected root path '{root}' to exist, but it does not."
    assert root.name == f"ws_{workspace_id}", f"Expected root path name to be 'ws_{workspace_id}', but got {root.name}"
    assert (root / "prompt" / "AGENTS.md").exists(), f"Expected 'AGENTS.md' in the prompt folder, but it was missing."
    assert (root / "memory" / "MEMORY.md").exists(), f"Expected 'MEMORY.md' in the memory folder, but it was missing."
    assert (root / "sessions").exists(), f"Expected a 'sessions' folder in the root directory, but it was not found."