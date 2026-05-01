import json
from pathlib import Path

from click.testing import CliRunner

from miminions.core.workspace import Workspace, WorkspaceManager
from miminions.interface.cli.main import cli
from miminions.workspace_fs.bootstrap import init_workspace


class FakeMinion:
    def __init__(self, reply: str = "assistant reply", error: Exception | None = None):
        self.reply = reply
        self.error = error
        self.prompts = []

    async def run(self, prompt: str) -> str:
        self.prompts.append(prompt)
        if self.error:
            raise self.error
        return self.reply


def _patch_prompt_runtime(monkeypatch, tmp_path: Path, fake_minion: FakeMinion | None = None) -> FakeMinion:
    fake = fake_minion or FakeMinion()

    monkeypatch.setattr(
        "miminions.interface.cli.prompt.get_config_dir",
        lambda: tmp_path / "config",
    )
    monkeypatch.setattr(
        "miminions.interface.cli.prompt._default_root_path",
        lambda workspace_id: tmp_path / "workspaces" / f"ws_{workspace_id}",
    )
    monkeypatch.setattr(
        "miminions.interface.cli.prompt.create_minion",
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
        assert len(session_files) == 1, f"Expected one session file, found {len(session_files)}"
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

    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}: {result.output}"
    assert result.output == "assistant reply\n", f"Expected assistant-only output, got: {result.output}"
    assert fake.prompts == ["book a chinese food restaurant at 6 pm today"]

    config_dir = tmp_path / "config"
    workspace_data = _read_workspace_data(config_dir)
    assert len(workspace_data) == 1, f"Expected one workspace, got: {workspace_data}"

    workspace_id, workspace = next(iter(workspace_data.items()))
    assert workspace["name"] == "default"

    root = tmp_path / "workspaces" / f"ws_{workspace_id}"
    assert workspace["root_path"] == str(root)
    assert (root / "prompt" / "AGENTS.md").exists()
    assert (root / "memory" / "MEMORY.md").exists()
    assert (root / "skills" / "core" / "SKILL.md").exists()

    records = _session_records(root)
    assert [record["role"] for record in records] == ["user", "assistant"]
    assert records[0]["content"] == "book a chinese food restaurant at 6 pm today"
    assert records[1]["content"] == "assistant reply"
    assert records[0]["meta"]["source"] == "cli-prompt"
    assert records[0]["meta"]["workspace_id"] == workspace_id


def test_prompt_ask_initializes_existing_workspace_without_root_path(tmp_path, monkeypatch):
    _patch_prompt_runtime(monkeypatch, tmp_path)

    config_dir = tmp_path / "config"
    manager = WorkspaceManager(config_dir)
    workspace = Workspace(name="existing")
    manager.save_workspaces({workspace.id: workspace})

    result = CliRunner().invoke(cli, ["prompt", "ask", "--workspace", "existing", "hello"])

    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}: {result.output}"

    workspace_data = _read_workspace_data(config_dir)
    saved_workspace = workspace_data[workspace.id]
    root = tmp_path / "workspaces" / f"ws_{workspace.id}"
    assert saved_workspace["root_path"] == str(root)
    assert (root / "prompt" / "AGENTS.md").exists()
    assert (root / "sessions").exists()


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

    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}: {result.output}"

    workspace_data = _read_workspace_data(config_dir)
    assert workspace_data[workspace.id]["root_path"] == str(root)
    records = _session_records(root)
    assert records[0]["content"] == "hello"


def test_prompt_ask_writes_to_requested_session(tmp_path, monkeypatch):
    _patch_prompt_runtime(monkeypatch, tmp_path)

    result = CliRunner().invoke(
        cli,
        ["prompt", "ask", "--session", "known-session", "hello", "there"],
    )

    assert result.exit_code == 0, f"Expected exit code 0, got {result.exit_code}: {result.output}"

    workspace_data = _read_workspace_data(tmp_path / "config")
    workspace_id = next(iter(workspace_data))
    root = tmp_path / "workspaces" / f"ws_{workspace_id}"
    records = _session_records(root, "known-session")

    assert [record["session_id"] for record in records] == ["known-session", "known-session"]
    assert records[0]["content"] == "hello there"


def test_prompt_ask_logs_runtime_error_and_exits_nonzero(tmp_path, monkeypatch):
    _patch_prompt_runtime(monkeypatch, tmp_path, FakeMinion(error=RuntimeError("runtime failed")))

    result = CliRunner().invoke(cli, ["prompt", "ask", "hello"])

    assert result.exit_code != 0, "Expected a non-zero exit code for runtime failure"
    assert "RuntimeError: runtime failed" in result.output

    workspace_data = _read_workspace_data(tmp_path / "config")
    workspace_id = next(iter(workspace_data))
    root = tmp_path / "workspaces" / f"ws_{workspace_id}"
    records = _session_records(root)

    assert [record["role"] for record in records] == ["user", "assistant"]
    assert records[1]["content"] == "[error] RuntimeError: runtime failed"
    assert records[1]["meta"]["error"] is True
