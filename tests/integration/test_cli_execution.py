"""Integration tests for execution CLI behavior."""

import json
from unittest.mock import patch

from click.testing import CliRunner

from miminions.cli.execution import execution
from miminions.workflow.models import AgentRunRecord, WorkflowRun, WorkflowTrace


def _auth_enabled():
    return patch("miminions.core.auth.is_authenticated", return_value=True)


def test_execution_interaction_list_json_output():
    runner = CliRunner()

    trace = WorkflowTrace()
    trace.add_agent_record(AgentRunRecord(prompt="ping", output="pong"))
    run = WorkflowRun(agent_name="session-s1", trace=trace)

    def _fake_load(path):
        if path.name == "interactions.json":
            return {"s1": [run.to_dict()]}
        return {}

    with _auth_enabled():
        with patch("miminions.cli.execution._load", side_effect=_fake_load):
            result = runner.invoke(execution, ["interaction", "list", "--session-id", "s1", "--json"])

    assert result.exit_code == 0, f"expect result.exit_code == 0, got {result.exit_code == 0}"
    payload = json.loads(result.output)
    assert payload[0]["index"] == 0, f"expect payload[0]['index'] == 0, got {payload[0]['index'] == 0}"
    assert payload[0]["workflow_run"]["id"] == run.id, f"expect payload[0]['workflow_run']['id'] == run.id, got {payload[0]['workflow_run']['id'] == run.id}"
