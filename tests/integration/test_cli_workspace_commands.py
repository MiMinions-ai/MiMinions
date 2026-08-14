"""Integration tests for workspace CLI command behavior."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from miminions.cli.workspace import workspace_cli
from miminions.core.workspace import Workspace


def _auth_enabled():
    return patch("miminions.core.auth.is_authenticated", return_value=True)


def test_workspace_list_and_show_json_output():
    runner = CliRunner()

    ws = Workspace(name="Demo", description="Workspace demo")
    manager = MagicMock()
    manager.load_workspaces.return_value = {ws.id: ws}

    with _auth_enabled():
        with patch("miminions.cli.workspace.get_workspace_manager", return_value=manager):
            list_result = runner.invoke(workspace_cli, ["list", "--json"])
            show_result = runner.invoke(workspace_cli, ["show", ws.id[:8], "--json"])

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0

    list_payload = json.loads(list_result.output)
    show_payload = json.loads(show_result.output)

    assert list_payload[0]["id"] == ws.id
    assert show_payload["id"] == ws.id
    assert "network_summary" in show_payload
