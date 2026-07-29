"""Tests for resilient, non-silent workspace loading."""

import logging

from miminions.core.workspace import WorkspaceManager


def test_corrupt_workspaces_file_returns_empty_and_warns(tmp_path, caplog):
    """A corrupt workspaces.json should not crash, but must log a warning."""
    (tmp_path / "workspaces.json").write_text("{ not valid json")
    manager = WorkspaceManager(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = manager.load_workspaces()

    assert result == {}
    assert any("workspaces" in r.message.lower() for r in caplog.records)


def test_missing_workspaces_file_returns_empty_silently(tmp_path, caplog):
    """A missing file is normal first-run state — no warning expected."""
    manager = WorkspaceManager(tmp_path)

    with caplog.at_level(logging.WARNING):
        result = manager.load_workspaces()

    assert result == {}
    assert not caplog.records
