import json
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

from click.testing import CliRunner

from miminions.core.workspace import Workspace, WorkspaceManager
from miminions.cli.main import cli
from miminions.workspace_fs.bootstrap import init_workspace


def _patch_prompt_runtime(monkeypatch, tmp_path: Path, fake_minion: MagicMock | None = None) -> MagicMock:
    fake = fake_minion or MagicMock()
    if not hasattr(fake, "run") or not isinstance(fake.run, AsyncMock):
        fake.run = AsyncMock(return_value="assistant reply")

    monkeypatch.setattr(
        "miminions.cli.prompt.get_config_dir",
        lambda: tmp_path / "config",
    )
    monkeypatch.setattr(
        "miminions.core.workspace.DEFAULT_WORKSPACES_ROOT",
        tmp_path / "workspaces",
    )
    monkeypatch.setattr(
        "miminions.cli.prompt.create_minion",
        lambda name, description: fake,
    )

    return fake


def _read_workspace_data(config_dir: Path) -> dict:
    return json.loads((config_dir / "workspaces.json").read_text(encoding="utf-8"))


def _session_records(root: Path, session_id: str | None = None) -> list[dict]:
    if session_id:
        session_file = root / "sessions" / f"{session_id}.jsonl"
    else:
        session_files = list((root / "sessions").glob("*.jsonl"))
        session_file_count = len(session_files)
        assert session_file_count == 1, f"expect exactly one session log file is created when session id is not specified as 1, got {session_file_count}"
        session_file = session_files[0]

    return [
        json.loads(line)
        for line in session_file.read_text(encoding="utf-8").splitlines()
        if line.strip()
    ]


def test_prompt_ask_creates_default_workspace_files_logs_and_prints(tmp_path, monkeypatch):
    fake = _patch_prompt_runtime(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        cli,
        ["prompt", "ask", "book a chinese food restaurant at 6 pm today"],
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"
    assert result.output == "assistant reply\n", f"expect prompt ask prints assistant runtime response followed by newline as 'assistant reply\n', got {result.output}"
    fake.run.assert_awaited_once_with("book a chinese food restaurant at 6 pm today")

    config_dir = tmp_path / "config"
    workspace_data = _read_workspace_data(config_dir)
    workspace_count = len(workspace_data)
    assert workspace_count == 1, f"expect prompt ask creates one default workspace record when no workspace is provided as 1, got {workspace_count}"

    workspace_id, workspace = next(iter(workspace_data.items()))
    assert workspace["name"] == "default", f"expect auto-created workspace uses default workspace name as 'default', got {workspace['name']}"

    root = tmp_path / "workspaces" / f"ws_{workspace_id}"
    assert workspace["root_path"] == str(root), f"expect workspace root_path points to generated ws directory under configured workspaces root as {str(root)}, got {workspace['root_path']}"
    agents_file_exists = (root / "prompt" / "AGENTS.md").exists()
    assert agents_file_exists, f"expect init_workspace creates prompt/AGENTS.md as True, got {agents_file_exists}"
    memory_file_exists = (root / "memory" / "MEMORY.md").exists()
    assert memory_file_exists, f"expect init_workspace creates memory/MEMORY.md as True, got {memory_file_exists}"
    skill_file_exists = (root / "skills" / "core" / "SKILL.md").exists()
    assert skill_file_exists, f"expect init_workspace creates skills/core/SKILL.md as True, got {skill_file_exists}"

    records = _session_records(root)
    record_roles = [record["role"] for record in records]
    assert record_roles == ["user", "assistant"], f"expect session log records user prompt followed by assistant reply for prompt ask flow as ['user', 'assistant'], got {record_roles}"
    assert records[0]["content"] == "book a chinese food restaurant at 6 pm today", f"expect first session record content stores original prompt text as 'book a chinese food restaurant at 6 pm today', got {records[0]['content']}"
    assert records[1]["content"] == "assistant reply", f"expect second session record content stores assistant runtime response as 'assistant reply', got {records[1]['content']}"
    assert records[0]["meta"]["source"] == "cli-prompt", f"expect user session metadata source is tagged as cli-prompt as 'cli-prompt', got {records[0]['meta']['source']}"
    assert records[0]["meta"]["workspace_id"] == workspace_id, f"expect workspace_id as {workspace_id}, got {records[0]['meta']['workspace_id']}"


def test_prompt_ask_initializes_existing_workspace_without_root_path(tmp_path, monkeypatch):
    _patch_prompt_runtime(monkeypatch, tmp_path)

    config_dir = tmp_path / "config"
    manager = WorkspaceManager(config_dir)
    workspace = Workspace(name="existing")
    manager.save_workspaces({workspace.id: workspace})

    result = CliRunner().invoke(cli, ["prompt", "ask", "--workspace", "existing", "hello"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"

    workspace_data = _read_workspace_data(config_dir)
    saved_workspace = workspace_data[workspace.id]
    root = tmp_path / "workspaces" / f"ws_{workspace.id}"
    assert saved_workspace["root_path"] == str(root), f"expect prompt ask backfills root_path for existing workspace without root_path as {str(root)}, got {saved_workspace['root_path']}"
    agents_file_exists = (root / "prompt" / "AGENTS.md").exists()
    assert agents_file_exists, f"expect prompt command initializes prompt/AGENTS.md for workspace without root_path as True, got {agents_file_exists}"
    sessions_dir_exists = (root / "sessions").exists()
    assert sessions_dir_exists, f"expect prompt command initializes sessions directory as True, got {sessions_dir_exists}"


def test_prompt_ask_reuses_existing_initialized_workspace_root(tmp_path, monkeypatch):
    _patch_prompt_runtime(monkeypatch, tmp_path)

    config_dir = tmp_path / "config"
    root = tmp_path / "custom-root"
    init_workspace(root)

    manager = WorkspaceManager(config_dir)
    workspace = Workspace(name="ready")
    workspace.root_path = str(root)
    manager.save_workspaces({workspace.id: workspace})

    result = CliRunner().invoke(cli, ["prompt", "ask", "--workspace", workspace.id[:8], "hello"])

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"

    workspace_data = _read_workspace_data(config_dir)
    root_path = workspace_data[workspace.id]["root_path"]
    assert root_path == str(root), f"expect prompt ask preserves configured workspace root_path for already initialized workspace as {str(root)}, got {root_path}"
    records = _session_records(root)
    assert records[0]["content"] == "hello", f"expect user prompt content is logged to session for existing initialized workspace flow as 'hello', got {records[0]['content']}"


def test_prompt_ask_writes_to_requested_session(tmp_path, monkeypatch):
    _patch_prompt_runtime(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        cli,
        ["prompt", "ask", "--session", "known-session", "hello", "there"],
    )

    assert result.exit_code == 0, f"expect cli exit code 0, got {result.exit_code} with output: {result.output}"

    workspace_data = _read_workspace_data(tmp_path / "config")
    workspace_id = next(iter(workspace_data))
    root = tmp_path / "workspaces" / f"ws_{workspace_id}"
    records = _session_records(root, "known-session")

    record_session_ids = [record["session_id"] for record in records]
    assert record_session_ids == ["known-session", "known-session"], f"expect both user and assistant records are written into requested known-session id as ['known-session', 'known-session'], got {record_session_ids}"
    assert records[0]["content"] == "hello there", f"expect prompt ask joins positional prompt args into one user message content entry as 'hello there', got {records[0]['content']}"


def test_prompt_ask_logs_runtime_error_and_exits_nonzero(tmp_path, monkeypatch):
    fake = MagicMock()
    fake.run = AsyncMock(side_effect=RuntimeError("runtime failed"))
    _patch_prompt_runtime(monkeypatch, tmp_path, fake)

    result = CliRunner().invoke(cli, ["prompt", "ask", "hello"])

    assert result.exit_code != 0, f"expect cli exit code != 0, got {result.exit_code} with output: {result.output}"
    assert "RuntimeError: runtime failed" in result.output, f"expect contains 'RuntimeError: runtime failed', got {result.output}"

    workspace_data = _read_workspace_data(tmp_path / "config")
    workspace_id = next(iter(workspace_data))
    root = tmp_path / "workspaces" / f"ws_{workspace_id}"
    records = _session_records(root)

    record_roles = [record["role"] for record in records]
    assert record_roles == ["user", "assistant"], f"expect runtime failure flow still logs paired user and assistant records to session history as ['user', 'assistant'], got {record_roles}"
    assert records[1]["content"] == "[error] RuntimeError: runtime failed", f"expect assistant error record content includes formatted runtime failure message as '[error] RuntimeError: runtime failed', got {records[1]['content']}"
    assert records[1]["meta"]["error"] is True, f"expect prompt runtime failure log marks assistant metadata error flag as True, got {records[1]['meta']['error']}"
