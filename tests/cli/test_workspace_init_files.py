from pathlib import Path
from click.testing import CliRunner

from miminions.interface.cli.workspace import workspace_cli


def test_workspace_add_with_init_files_creates_root_path_and_files(tmp_path, monkeypatch):
    
    monkeypatch.setattr(
    "miminions.interface.cli.workspace.require_auth",
    lambda: (lambda f: f),
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

    assert result.exit_code == 0

    config_dir = tmp_path
    workspaces_file = config_dir / "workspaces.json"
    assert workspaces_file.exists()

    import json
    data = json.loads(workspaces_file.read_text(encoding="utf-8"))
    assert len(data) == 1

    workspace_id, workspace_data = next(iter(data.items()))
    assert workspace_data["name"] == "phase6-test"
    assert workspace_data["root_path"] is not None

    root = Path(workspace_data["root_path"])
    assert root.exists()
    assert (root / "prompt" / "AGENTS.md").exists()
    assert (root / "prompt" / "USER.md").exists()
    assert (root / "prompt" / "TOOLS.md").exists()
    assert (root / "prompt" / "IDENTITY.md").exists()
    assert (root / "memory" / "MEMORY.md").exists()
    assert (root / "memory" / "HISTORY.md").exists()
    assert (root / "sessions").exists()
    assert (root / "data").exists()


def test_workspace_init_files_sets_root_path_for_existing_workspace(tmp_path, monkeypatch):
    
    monkeypatch.setattr(
        "miminions.interface.cli.workspace.require_auth",
        lambda: (lambda f: f),
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
    assert add_result.exit_code == 0

    init_result = runner.invoke(
        workspace_cli,
        [
            "init-files",
            "existing-ws",
        ],
    )
    assert init_result.exit_code == 0

    import json
    workspaces_file = tmp_path / "workspaces.json"
    data = json.loads(workspaces_file.read_text(encoding="utf-8"))
    assert len(data) == 1

    workspace_id, workspace_data = next(iter(data.items()))
    assert workspace_data["root_path"] is not None

    root = Path(workspace_data["root_path"])
    assert root.exists()
    assert root.name == f"ws_{workspace_id}"
    assert (root / "prompt" / "AGENTS.md").exists()
    assert (root / "memory" / "MEMORY.md").exists()
    assert (root / "sessions").exists()