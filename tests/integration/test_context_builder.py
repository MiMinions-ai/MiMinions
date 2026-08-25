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

    assert "# MiMinions Agent Context" in context, f"expect contains '# MiMinions Agent Context', got {context}"
    assert "workspace_name: Test Workspace" in context, f"expect contains 'workspace_name: Test Workspace', got {context}"
    assert "workspace_id: ws_123" in context, f"expect contains 'workspace_id: ws_123', got {context}"
    assert "## Prompt Files" in context, f"expect contains '## Prompt Files', got {context}"
    assert "### AGENTS.md" in context, f"expect contains '### AGENTS.md', got {context}"
    assert "Use the agent carefully." in context, f"expect contains 'Use the agent carefully.', got {context}"
    assert "## Memory" in context, f"expect contains '## Memory', got {context}"
    assert "Stable fact: user prefers inspectable systems." in context, f"expect contains 'Stable fact: user prefers inspectable systems.', got {context}"
    assert "## Workspace Graph Summary" in context, f"expect contains '## Workspace Graph Summary', got {context}"
    assert "- agent: 2" in context, f"expect contains '- agent: 2', got {context}"
    assert "- tool: 1" in context, f"expect contains '- tool: 1', got {context}"
    assert "high-priority-rule" in context, f"expect contains 'high-priority-rule', got {context}"
    assert "low-priority-rule" in context, f"expect contains 'low-priority-rule', got {context}"
    assert "- active_session_id" in context, f"expect contains '- active_session_id', got {context}"
    assert "- mode" in context, f"expect contains '- mode', got {context}"
    assert "## Skills Index" in context, f"expect contains '## Skills Index', got {context}"
    assert "- core:" in context, f"expect contains '- core:', got {context}"
    assert "Instruction: read a skill file before using it." in context, f"expect contains 'Instruction: read a skill file before using it.', got {context}"


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

    assert "workspace_name: Empty Workspace" in context, f"expect contains 'workspace_name: Empty Workspace', got {context}"
    assert "- No nodes found." in context, f"expect contains '- No nodes found.', got {context}"
    assert "- No rules found." in context, f"expect contains '- No rules found.', got {context}"
    assert "- No state keys found." in context, f"expect contains '- No state keys found.', got {context}"


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

    assert "## Global Knowledge" in context, f"expect contains '## Global Knowledge', got {context}"
    assert "- User prefers concise commit messages." in context, f"expect contains '- User prefers concise commit messages.', got {context}"
    assert "- Always run tests before pushing." in context, f"expect contains '- Always run tests before pushing.', got {context}"
    # Global Knowledge must appear before Memory
    global_knowledge_index = context.index("## Global Knowledge")
    memory_index = context.index("## Memory")
    assert global_knowledge_index < memory_index, f"expect context.index('## Global Knowledge') < context.index('## Memory'), got {global_knowledge_index}"


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

    assert "## Memory" in context, f"expect contains '## Memory', got {context}"
    assert "## Global Knowledge" not in context, f"expect not contains '## Global Knowledge', got {context}"


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

    assert not called, f"expect global insight fetch not called when global_top_k=0, got calls: {called}"
    assert "## Global Knowledge" not in context, f"expect not contains '## Global Knowledge', got {context}"