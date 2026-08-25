"""Integration tests for workflow CLI behavior."""

import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from miminions.cli.workflow import workflow_cli


def _write(path: Path, payload: dict) -> None:
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _read(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _patch_auth_enabled():
    return patch("miminions.core.auth.is_authenticated", return_value=True)


def test_workflow_add_rejects_unknown_agents(temp_config_dir):
    runner = CliRunner()
    _write(temp_config_dir / "agents.json", {"a1": {"name": "Agent One"}})

    with _patch_auth_enabled():
        with patch("miminions.cli.workflow.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(
                workflow_cli,
                [
                    "add",
                    "--name",
                    "Flow",
                    "--description",
                    "Desc",
                    "--agents",
                    "a1,missing",
                ],
            )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Unknown agent id(s): missing" in result.output, f"expect workflow add command validates agent ids and reports unknown ids in user-facing output as 'Unknown agent id(s): missing', got {result.output}"


def test_workflow_update_rejects_unknown_agents(temp_config_dir):
    runner = CliRunner()
    _write(temp_config_dir / "agents.json", {"a1": {"name": "Agent One"}})
    _write(
        temp_config_dir / "workflows.json",
        {
            "wf1": {
                "name": "Flow",
                "description": "Desc",
                "agents": ["a1"],
                "status": "stopped",
                "tasks": [],
                "created_at": "",
                "updated_at": None,
            }
        },
    )

    with _patch_auth_enabled():
        with patch("miminions.cli.workflow.get_config_dir", return_value=temp_config_dir):
            result = runner.invoke(workflow_cli, ["update", "wf1", "--agents", "missing"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert "Unknown agent id(s): missing" in result.output, f"expect workflow update command validates agent ids and reports unknown ids in user-facing output as 'Unknown agent id(s): missing', got {result.output}"

    workflows = _read(temp_config_dir / "workflows.json")
    assert workflows["wf1"]["agents"] == ["a1"], f"expect failed workflow update leaves persisted workflow agent list unchanged as ['a1'], got {workflows['wf1']['agents']}"
