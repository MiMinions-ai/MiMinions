"""Integration tests for --json output flags on list/show commands."""

import json
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from miminions.cli.agent import agent_cli
from miminions.cli.execution import execution
from miminions.cli.knowledge import knowledge_cli
from miminions.cli.task import task_cli
from miminions.cli.workspace import workspace_cli
from miminions.core.workspace import Workspace
from miminions.workflow.models import AgentRunRecord, WorkflowRun, WorkflowTrace


def _auth_enabled():
    return patch("miminions.core.auth.is_authenticated", return_value=True)


def test_agent_list_and_show_json_output():
    runner = CliRunner()
    agents = {
        "research_agent": {
            "name": "Research Agent",
            "description": "Finds facts",
            "type": "assistant",
            "status": "inactive",
        }
    }

    with patch("miminions.cli.agent.load_agents", return_value=agents):
        list_result = runner.invoke(agent_cli, ["list", "--json"])
        show_result = runner.invoke(agent_cli, ["show", "research_agent", "--json"])

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0

    list_payload = json.loads(list_result.output)
    show_payload = json.loads(show_result.output)

    assert list_payload[0]["id"] == "research_agent"
    assert show_payload["id"] == "research_agent"
    assert show_payload["name"] == "Research Agent"


def test_task_list_and_show_json_output():
    runner = CliRunner()
    tasks = {
        "task01": {
            "title": "Write docs",
            "description": "Update CLI docs",
            "priority": "high",
            "status": "pending",
            "agent": "research_agent",
            "created_at": "2026-07-13T00:00:00+00:00",
            "updated_at": None,
        }
    }

    with _auth_enabled():
        with patch("miminions.cli.task.load_tasks", return_value=tasks):
            list_result = runner.invoke(task_cli, ["list", "--json"])
            show_result = runner.invoke(task_cli, ["show", "task01", "--json"])

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0

    list_payload = json.loads(list_result.output)
    show_payload = json.loads(show_result.output)

    assert list_payload[0]["id"] == "task01"
    assert show_payload["id"] == "task01"
    assert show_payload["title"] == "Write docs"


def test_knowledge_list_and_show_json_output():
    runner = CliRunner()
    knowledge = {
        "kn01": {
            "title": "Deploy Steps",
            "content": "...",
            "category": "ops",
            "tags": ["deploy"],
            "version": "1.0",
            "status": "active",
            "created_at": "2026-07-13T00:00:00+00:00",
            "updated_at": None,
            "versions": [{"version": "1.0", "content": "...", "timestamp": "2026-07-13T00:00:00+00:00"}],
        }
    }

    with _auth_enabled():
        with patch("miminions.cli.knowledge.load_knowledge", return_value=knowledge):
            list_result = runner.invoke(knowledge_cli, ["list", "--json"])
            show_result = runner.invoke(knowledge_cli, ["show", "kn01", "--json"])

    assert list_result.exit_code == 0
    assert show_result.exit_code == 0

    list_payload = json.loads(list_result.output)
    show_payload = json.loads(show_result.output)

    assert list_payload[0]["id"] == "kn01"
    assert show_payload["id"] == "kn01"
    assert show_payload["title"] == "Deploy Steps"


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

    assert result.exit_code == 0
    payload = json.loads(result.output)
    assert payload[0]["index"] == 0
    assert payload[0]["workflow_run"]["id"] == run.id
