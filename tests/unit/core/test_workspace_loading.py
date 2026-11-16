"""Tests for resilient, non-silent workspace loading."""

import json
import logging

import pytest

from miminions.core.workspace import (
    WORKSPACE_SCHEMA_VERSION,
    Workspace,
    WorkspaceManager,
)


def test_corrupt_workspaces_file_returns_empty_and_warns(tmp_path, caplog):
    """A corrupt workspaces.json should not crash, but must log a warning."""
    (tmp_path / "workspaces.json").write_text("{ not valid json")
    manager = WorkspaceManager(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = manager.load_workspaces()

    assert result == {}, f"expect {{}}, got {result}"
    assert any("workspaces" in r.message.lower() for r in caplog.records), f"expect at least one item matching 'workspaces' in r.message.lower(), got none in {caplog.records}"


def test_missing_workspaces_file_returns_empty_silently(tmp_path, caplog):
    """A missing file is normal first-run state — no warning expected."""
    manager = WorkspaceManager(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = manager.load_workspaces()

    assert result == {}, f"expect {{}}, got {result}"
    assert not caplog.records, f"expect caplog.records empty, got {caplog.records}"


def test_to_dict_stamps_current_schema_version():
    """Every persisted record must carry the current schema version."""
    workspace = Workspace(name="Stamped")

    assert workspace.to_dict()["schema_version"] == WORKSPACE_SCHEMA_VERSION, f"expect WORKSPACE_SCHEMA_VERSION, got {workspace.to_dict()['schema_version']}"


def test_record_without_schema_version_is_rejected(tmp_path):
    legacy = {"ws1": {"id": "ws1", "name": "Legacy", "description": ""}}
    path = tmp_path / "workspaces.json"
    original = json.dumps(legacy)
    path.write_text(original)
    manager = WorkspaceManager(tmp_path)

    with pytest.raises(ValueError, match="unsupported schema_version None"):
        manager.load_workspaces()

    assert path.read_text() == original


def test_save_stamps_schema_version_and_leaves_no_tmp_file(tmp_path):
    """save_workspaces writes the version stamp via an atomic replace."""
    manager = WorkspaceManager(tmp_path)
    workspace = Workspace(name="Stamped")

    manager.save_workspaces({workspace.id: workspace})

    raw = json.loads((tmp_path / "workspaces.json").read_text())
    assert raw[workspace.id]["schema_version"] == WORKSPACE_SCHEMA_VERSION, f"expect WORKSPACE_SCHEMA_VERSION, got {raw[workspace.id]['schema_version']}"
    temp_file_exists = (tmp_path / "workspaces.tmp").exists()
    assert not temp_file_exists, f"expect save_workspaces atomic replace removes workspaces.tmp, got {temp_file_exists}"


@pytest.mark.parametrize("version", [None, "1", True, 1.0, 0, -1, 99])
def test_unsupported_schema_version_is_rejected_without_changing_store(tmp_path, version):
    records = {
        "good": Workspace(id="good", name="Current").to_dict(),
        "bad": {**Workspace(id="bad", name="Unsupported").to_dict(), "schema_version": version},
    }
    path = tmp_path / "workspaces.json"
    original = json.dumps(records)
    path.write_text(original)
    manager = WorkspaceManager(tmp_path)

    with pytest.raises(ValueError, match="unsupported schema_version"):
        manager.load_workspaces()

    with pytest.raises(ValueError, match="unsupported schema_version"):
        Workspace.from_dict(records["bad"])

    assert path.read_text() == original
