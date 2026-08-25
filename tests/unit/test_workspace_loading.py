"""Tests for resilient, non-silent workspace loading."""

import json
import logging

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


def test_legacy_record_without_schema_version_loads_silently(tmp_path, caplog):
    """Records saved before versioning existed are treated as v1 — no warning."""
    legacy = {"ws1": {"id": "ws1", "name": "Legacy", "description": ""}}
    (tmp_path / "workspaces.json").write_text(json.dumps(legacy))
    manager = WorkspaceManager(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = manager.load_workspaces()

    assert result["ws1"].name == "Legacy", f"expect 'Legacy', got {result['ws1'].name}"
    assert not caplog.records, f"expect caplog.records empty, got {caplog.records}"


def test_save_stamps_schema_version_and_leaves_no_tmp_file(tmp_path):
    """save_workspaces writes the version stamp via an atomic replace."""
    manager = WorkspaceManager(tmp_path)
    workspace = Workspace(name="Stamped")

    manager.save_workspaces({workspace.id: workspace})

    raw = json.loads((tmp_path / "workspaces.json").read_text())
    assert raw[workspace.id]["schema_version"] == WORKSPACE_SCHEMA_VERSION, f"expect WORKSPACE_SCHEMA_VERSION, got {raw[workspace.id]['schema_version']}"
    temp_file_exists = (tmp_path / "workspaces.tmp").exists()
    assert not temp_file_exists, f"expect save_workspaces atomic replace removes workspaces.tmp, got {temp_file_exists}"


def test_invalid_schema_version_warns_but_does_not_discard_file(tmp_path, caplog):
    """One tampered record must not take down the other workspaces in the file."""
    records = {
        "bad": {"schema_version": None, "id": "bad", "name": "Tampered"},
        "good": {"schema_version": 1, "id": "good", "name": "Fine"},
    }
    (tmp_path / "workspaces.json").write_text(json.dumps(records))
    manager = WorkspaceManager(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = manager.load_workspaces()

    assert result["bad"].name == "Tampered", f"expect 'Tampered', got {result['bad'].name}"
    assert result["good"].name == "Fine", f"expect 'Fine', got {result['good'].name}"
    assert any("invalid schema_version" in r.message for r in caplog.records), f"expect at least one item matching 'invalid schema_version' in r.message, got none in {caplog.records}"


def test_newer_schema_version_warns_but_loads(tmp_path, caplog):
    """A record from a future format version loads best-effort with a warning."""
    record = {"ws1": {"schema_version": 99, "id": "ws1", "name": "Future"}}
    (tmp_path / "workspaces.json").write_text(json.dumps(record))
    manager = WorkspaceManager(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = manager.load_workspaces()

    assert result["ws1"].name == "Future", f"expect 'Future', got {result['ws1'].name}"
    assert any("schema_version" in r.message for r in caplog.records), f"expect at least one item matching 'schema_version' in r.message, got none in {caplog.records}"
