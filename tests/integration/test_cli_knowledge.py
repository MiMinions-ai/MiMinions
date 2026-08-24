"""Integration tests for knowledge CLI behavior."""

import json
from unittest.mock import patch

from click.testing import CliRunner

from miminions.cli.knowledge import knowledge_cli


def _auth_enabled():
    return patch("miminions.core.auth.is_authenticated", return_value=True)


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
            "versions": [
                {
                    "version": "1.0",
                    "content": "...",
                    "timestamp": "2026-07-13T00:00:00+00:00",
                }
            ],
        }
    }

    with _auth_enabled():
        with patch("miminions.cli.knowledge.load_knowledge", return_value=knowledge):
            list_result = runner.invoke(knowledge_cli, ["list", "--json"])
            show_result = runner.invoke(knowledge_cli, ["show", "kn01", "--json"])

    assert list_result.exit_code == 0, f"expect list_result.exit_code == 0, got {list_result.exit_code == 0}"
    assert show_result.exit_code == 0, f"expect show_result.exit_code == 0, got {show_result.exit_code == 0}"

    list_payload = json.loads(list_result.output)
    show_payload = json.loads(show_result.output)

    assert list_payload[0]["id"] == "kn01", f"expect list_payload[0]['id'] == 'kn01', got {list_payload[0]['id'] == 'kn01'}"
    assert show_payload["id"] == "kn01", f"expect show_payload['id'] == 'kn01', got {show_payload['id'] == 'kn01'}"
    assert show_payload["title"] == "Deploy Steps", f"expect show_payload['title'] == 'Deploy Steps', got {show_payload['title'] == 'Deploy Steps'}"
