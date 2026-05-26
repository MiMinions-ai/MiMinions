from pathlib import Path

from miminions.context import ContextBuilder
from miminions.memory.md_store import write_memory
from miminions.workspace_fs.bootstrap import init_workspace


class DummyRule:
    def __init__(self, name: str, priority: int, rule_type: str | None = None):
        self.name = name
        self.priority = priority
        self.type = rule_type


class DummyNode:
    def __init__(self, node_type: str):
        self.type = node_type


class DummyWorkspace:
    def __init__(self, root_path: str):
        self.id = "ws_123"
        self.name = "Test Workspace"
        self.root_path = root_path
        self.nodes = [
            DummyNode("agent"),
            DummyNode("agent"),
            DummyNode("tool"),
        ]
        self.rules = [
            DummyRule("high-priority-rule", 100, "policy"),
            DummyRule("low-priority-rule", 5, "hint"),
        ]
        self.state = {
            "active_session_id": "sess_1",
            "mode": "chat",
        }


def test_context_builder_includes_prompt_memory_and_summary(tmp_path: Path):
    init_workspace(tmp_path)

    prompt_agents = tmp_path / "prompt" / "AGENTS.md"
    prompt_agents.write_text("# Agents\n\nUse the agent carefully.\n", encoding="utf-8")

    write_memory(tmp_path, "# Memory\n\nStable fact: user prefers inspectable systems.\n")

    skill_dir = tmp_path / "skills" / "core"
    skill_dir.mkdir(parents=True, exist_ok=True)
    (skill_dir / "SKILL.md").write_text("# Core Skill\n", encoding="utf-8")

    workspace = DummyWorkspace(str(tmp_path))
    builder = ContextBuilder()

    context = builder.build(workspace, tmp_path)

    assert "# MiMinions Agent Context" in context, f"#Expected 'MiMinions Agent Context' in context, but got: {context}"
    assert "workspace_name: Test Workspace" in context, f"Expected 'workspace_name: Test Workspace' in context, but got: {context}"
    assert "workspace_id: ws_123" in context, f"Expected 'workspace_id: ws_123' in context, but got: {context}"
    assert "## Prompt Files" in context, f"Expected '## Prompt Files' in context, but got: {context}"
    assert "### AGENTS.md" in context, f"Expected '### AGENTS.md' in context, but got: {context}"
    assert "Use the agent carefully." in context, f"Expected 'Use the agent carefully.' in context, but got: {context}"
    assert "## Memory" in context, f"Expected '## Memory' in context, but got: {context}"
    assert "Stable fact: user prefers inspectable systems." in context, f"Expected 'Stable fact: user prefers inspectable systems.' in context, but got: {context}"
    assert "## Workspace Graph Summary" in context, f"Expected '## Workspace Graph Summary' in context, but got: {context}"
    assert "- agent: 2" in context, f"Expected '- agent: 2' in context, but got: {context}"
    assert "- tool: 1" in context, f"Expected '- tool: 1' in context, but got: {context}"
    assert "high-priority-rule" in context, f"Expected 'high-priority-rule' in context, but got: {context}"
    assert "low-priority-rule" in context, f"Expected 'low-priority-rule' in context, but got: {context}"
    assert "- active_session_id" in context, f"Expected '- active_session_id' in context, but got: {context}"
    assert "- mode" in context, f"Expected '- mode' in context, but got: {context}"
    assert "## Skills Index" in context, f"Expected '## Skills Index' in context, but got: {context}"
    assert "- core:" in context, f"Expected '- core:' in context, but got: {context}"
    assert "Instruction: read a skill file before using it." in context, f"Expected 'Instruction: read a skill file before using it.' in context, but got: {context}"


def test_context_builder_handles_empty_workspace_sections(tmp_path: Path):
    init_workspace(tmp_path)

    workspace = {
        "id": "ws_empty",
        "name": "Empty Workspace",
        "root_path": str(tmp_path),
        "nodes": [],
        "rules": [],
        "state": {},
    }

    builder = ContextBuilder()
    context = builder.build(workspace, tmp_path)

    assert "workspace_name: Empty Workspace" in context, f"Expected 'workspace_name: Empty Workspace' in context, but got: {context}"
    assert "- No nodes found." in context, f"Expected '- No nodes found.' in context, but got: {context}"
    assert "- No rules found." in context, f"Expected '- No rules found.' in context, but got: {context}"
    assert "- No state keys found." in context, f"Expected '- No state keys found.' in context, but got: {context}"


def test_context_builder_injects_global_knowledge_when_available(tmp_path: Path, monkeypatch):
    """Global Knowledge section appears when SQLite returns insights."""
    init_workspace(tmp_path)

    monkeypatch.setattr(
        "miminions.context.context_builder._fetch_global_insights",
        lambda top_k, db_path: ["User prefers concise commit messages.", "Always run tests before pushing."],
    )

    workspace = {
        "id": "ws_global",
        "name": "Global WS",
        "root_path": str(tmp_path),
        "nodes": [],
        "rules": [],
        "state": {},
    }

    context = ContextBuilder().build(workspace, tmp_path)

    assert "## Global Knowledge" in context, f"Expected '## Global Knowledge' in context, but got: {context}"
    assert "- User prefers concise commit messages." in context
    assert "- Always run tests before pushing." in context
    # Global Knowledge must appear before Memory
    assert context.index("## Global Knowledge") < context.index("## Memory")


def test_context_builder_skips_global_knowledge_when_sqlite_unavailable(tmp_path: Path, monkeypatch):
    """Context builds without error and omits Global Knowledge when SQLite is down."""
    init_workspace(tmp_path)

    monkeypatch.setattr(
        "miminions.context.context_builder._fetch_global_insights",
        lambda top_k, db_path: [],
    )

    workspace = {
        "id": "ws_nosql",
        "name": "No SQL WS",
        "root_path": str(tmp_path),
        "nodes": [],
        "rules": [],
        "state": {},
    }

    context = ContextBuilder().build(workspace, tmp_path)

    assert "## Memory" in context, "Context must still include Memory section"
    assert "## Global Knowledge" not in context, "Global Knowledge must be absent when SQLite returns nothing"


def test_context_builder_omits_global_knowledge_when_top_k_zero(tmp_path: Path, monkeypatch):
    """Setting global_top_k=0 disables global injection entirely."""
    init_workspace(tmp_path)

    called = []
    monkeypatch.setattr(
        "miminions.context.context_builder._fetch_global_insights",
        lambda top_k, db_path: called.append(1) or ["some insight"],
    )

    workspace = {
        "id": "ws_disabled",
        "name": "Disabled WS",
        "root_path": str(tmp_path),
        "nodes": [],
        "rules": [],
        "state": {},
    }

    context = ContextBuilder(global_top_k=0).build(workspace, tmp_path)

    assert not called, "_fetch_global_insights must not be called when global_top_k=0"
    assert "## Global Knowledge" not in context