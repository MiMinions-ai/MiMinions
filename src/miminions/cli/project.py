"""Project selection shared by chat and prompt; state stays in MiMinions home."""

from __future__ import annotations

from pathlib import Path

import click


def project_options(func):
    func = click.option("--no-discovery", is_flag=True, help="Disable project discovery and use the existing workspace workflow.")(func)
    return click.option("--project", type=click.Path(exists=True, file_okay=False, path_type=Path),
                        default=None, help="Use this project directory instead of detecting the current directory.")(func)


def select_project(home: Path, workspace_ref: str | None, project: Path | None, no_discovery: bool,
                   *, init_files: bool = False) -> str | None:
    if project is not None and (workspace_ref is not None or no_discovery):
        raise click.UsageError("--project cannot be combined with --workspace or --no-discovery.")
    if workspace_ref is not None or no_discovery:
        return workspace_ref
    from miminions.workspace_fs.discovery import canonical_project, detect_project, project_key
    from miminions.core.workspace import Workspace, WorkspaceManager, ensure_workspace
    from miminions.execution.processes import InstanceLock

    try:
        root = canonical_project(project or Path.cwd())
        if project is None and not detect_project(root):
            return None
        workspace_id = f"project_{project_key(root)}"
        with InstanceLock(home / "execution-workspace.lock"):
            manager = WorkspaceManager(home)
            workspaces = manager.load_workspaces()
            if workspace_id not in workspaces:
                workspace = Workspace(id=workspace_id, name=root.name, description=f"Project at {root}")
                workspace.root_path = str((home / "workspaces" / f"ws_{workspace_id}").resolve())
                workspace.state["project_root"] = str(root)
                workspaces[workspace_id] = workspace
                manager.save_workspaces(workspaces)
            if init_files:
                ensure_workspace(manager, workspace_id, init_files=True)
        return workspace_id
    except (OSError, ValueError) as exc:
        raise click.ClickException(str(exc)) from exc


def load_project_context(workspace, state_root: Path):
    from miminions.workspace_fs.discovery import scan_project

    project_root = workspace.state.get("project_root")
    if project_root:
        return scan_project(project_root, state_root / "discovery.json")
    return None
