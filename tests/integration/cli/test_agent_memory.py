"""Integration tests for `miminions agent` memory commands (both backends)."""

import re

from click.testing import CliRunner

from miminions.cli.agent import agent_cli, load_agents, save_agents

AGENT_ID = "mem_agent"


def _runner_with_agent():
    save_agents({AGENT_ID: {"name": "Mem Agent", "goal": None}})
    return CliRunner()


def _invoke(runner, args):
    result = runner.invoke(agent_cli, args)
    assert result.exit_code == 0, (
        f"expect cli exit code 0 for {args}, got {result.exit_code} with output: {result.output}"
    )
    return result


def test_md_backend_full_flow(tmp_path):
    runner = _runner_with_agent()
    workspace = tmp_path / "ws"

    result = _invoke(runner, ["memory-attach", AGENT_ID, "--backend", "md", "--workspace", str(workspace)])
    target = f"Memory backend 'md' attached to agent '{AGENT_ID}'."
    assert target in result.output, f"expect {target} in result.output, got {result.output}"
    attached = load_agents()[AGENT_ID].get("memory_backend")
    assert attached == "md", f"expect persisted memory_backend to be 'md', got {attached}"

    result = _invoke(runner, ["memory-store", AGENT_ID, "likes tea", "--section", "Prefs"])
    target = "Stored memory section 'Prefs'"
    assert target in result.output, f"expect {target} in result.output, got {result.output}"

    result = _invoke(runner, ["memory-recall", AGENT_ID, "tea"])
    assert "Prefs" in result.output and "likes tea" in result.output, (
        f"expect recalled section 'Prefs' with 'likes tea' in result.output, got {result.output}"
    )

    _invoke(runner, ["memory-update", AGENT_ID, "Prefs", "likes coffee"])
    result = _invoke(runner, ["memory-recall", AGENT_ID, "coffee"])
    assert "likes coffee" in result.output, (
        f"expect updated text 'likes coffee' in result.output, got {result.output}"
    )

    _invoke(runner, ["ingest-document", AGENT_ID, _write_doc(tmp_path), "--section", "Doc"])
    result = _invoke(runner, ["memory-recall", AGENT_ID, "chunked"])
    assert "Doc" in result.output, f"expect ingested section 'Doc' in result.output, got {result.output}"

    _invoke(runner, ["memory-delete", AGENT_ID, "Prefs"])
    result = _invoke(runner, ["memory-recall", AGENT_ID, "coffee"])
    target = "No memories found."
    assert target in result.output, f"expect {target} after delete in result.output, got {result.output}"


def _write_doc(tmp_path):
    doc = tmp_path / "notes.txt"
    doc.write_text("chunked document body for ingestion", encoding="utf-8")
    return str(doc)


def test_sqlite_backend_full_flow(tmp_path):
    runner = _runner_with_agent()
    db_path = str(tmp_path / "mem.db")

    _invoke(runner, ["memory-attach", AGENT_ID, "--backend", "sqlite", "--db", db_path])

    result = _invoke(runner, ["memory-store", AGENT_ID, "Python is a language", "--meta", "topic=python"])
    match = re.search(r"Stored memory (\S+)", result.output)
    assert match, f"expect a 'Stored memory <id>' line in result.output, got {result.output}"
    memory_id = match.group(1)

    result = _invoke(runner, ["memory-recall", AGENT_ID, "Python"])
    assert memory_id in result.output, (
        f"expect recalled id {memory_id} in result.output, got {result.output}"
    )

    _invoke(runner, ["memory-update", AGENT_ID, memory_id, "Python is a programming language"])
    _invoke(runner, ["ingest-document", AGENT_ID, _write_doc(tmp_path)])
    _invoke(runner, ["memory-delete", AGENT_ID, memory_id])

    result = runner.invoke(agent_cli, ["memory-delete", AGENT_ID, memory_id])
    assert result.exit_code != 0, (
        f"expect cli exit code != 0 deleting a missing memory, got {result.exit_code} "
        f"with output: {result.output}"
    )


def test_memory_commands_require_attach():
    runner = _runner_with_agent()
    result = runner.invoke(agent_cli, ["memory-store", AGENT_ID, "orphan text", "--section", "X"])
    assert result.exit_code != 0, (
        f"expect cli exit code != 0 without attach, got {result.exit_code} with output: {result.output}"
    )
    target = "No memory backend attached"
    assert target in result.output, f"expect {target} in result.output, got {result.output}"
