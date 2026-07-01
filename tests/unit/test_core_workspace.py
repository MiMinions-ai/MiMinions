import json

import pytest

from miminions.core.workspace import (
    Node,
    NodeType,
    Rule,
    RulePriority,
    Workspace,
    WorkspaceManager,
    default_workspace_root,
    ensure_workspace,
    resolve_workspace,
)


def test_node_rule_and_workspace_serialization_round_trip():
    node = Node(id="n1", name="Agent", type=NodeType.AGENT, properties={"role": "a"})
    rule = Rule(
        id="r1",
        name="Always",
        priority=RulePriority.CRITICAL,
        condition={"type": "always"},
        action={"type": "notify"},
    )
    workspace = Workspace(id="w1", name="WS", nodes={node.id: node}, rules={rule.id: rule})

    restored = Workspace.from_dict(workspace.to_dict())

    assert restored.id == "w1"
    assert restored.nodes["n1"].type is NodeType.AGENT
    assert restored.rules["r1"].priority is RulePriority.CRITICAL


def test_node_connections_are_bidirectional_and_removed_cleanly():
    workspace = Workspace(name="Graph")
    first = Node(id="a", name="A")
    second = Node(id="b", name="B")
    workspace.add_node(first)
    workspace.add_node(second)

    assert workspace.connect_nodes("a", "b") is True
    assert workspace.connect_nodes("a", "missing") is False
    assert first.connections == ["b"]
    assert second.connections == ["a"]
    assert workspace.get_network_summary()["total_connections"] == 1

    assert workspace.disconnect_nodes("a", "b") is True
    assert first.connections == []
    assert second.connections == []
    assert workspace.disconnect_nodes("a", "b") is False

    workspace.connect_nodes("a", "b")
    assert workspace.remove_node("b") is True
    assert "b" not in workspace.nodes
    assert first.connections == []
    assert workspace.remove_node("missing") is False


def test_rule_sorting_enabled_filtering_and_supported_conditions():
    workspace = Workspace(name="Rules")
    workspace.state = {"status": "ready", "count": 2}
    workspace.add_node(Node(id="agent", type=NodeType.AGENT))
    workspace.add_rule(
        Rule(id="low", name="Low", priority=RulePriority.LOW, condition={}, action={})
    )
    workspace.add_rule(
        Rule(
            id="high",
            name="High",
            priority=RulePriority.HIGH,
            condition={"type": "state_equals", "key": "status", "value": "ready"},
            action={"type": "high"},
        )
    )
    workspace.add_rule(
        Rule(id="off", name="Off", priority=RulePriority.CRITICAL, enabled=False)
    )

    assert [rule.id for rule in workspace.get_all_rules()] == ["high", "low"]
    assert [action["rule_id"] for action in workspace.evaluate_state_logic()] == [
        "high",
        "low",
    ]

    assert workspace._evaluate_condition({"type": "always"}) is True
    assert workspace._evaluate_condition({"type": "state_equals", "key": "count", "value": 2})
    assert workspace._evaluate_condition({"type": "node_count", "operator": ">=", "count": 1})
    assert workspace._evaluate_condition({"type": "node_count", "operator": "<=", "count": 1})
    assert workspace._evaluate_condition({"type": "node_count", "operator": "==", "count": 1})
    assert workspace._evaluate_condition({"type": "node_count", "operator": ">", "count": 0})
    assert workspace._evaluate_condition({"type": "node_count", "operator": "<", "count": 2})
    assert workspace._evaluate_condition({"type": "node_type_exists", "node_type": "agent"})
    assert workspace._evaluate_condition({"type": "unknown"}) is False


def test_rule_inheritance_copies_parent_and_inherited_rules():
    grandparent = Workspace(name="Grandparent")
    grandparent.inherited_rules["g"] = Rule(
        id="g", name="Grand", inherited_from="Origin:g", priority=RulePriority.MEDIUM
    )
    parent = Workspace(id="parent", name="Parent")
    parent.rules["p"] = Rule(id="p", name="Parent Rule", priority=RulePriority.HIGH)
    parent.inherited_rules = grandparent.inherited_rules
    child = Workspace(name="Child")

    child.inherit_rules_from(parent)

    names = {rule.name for rule in child.inherited_rules.values()}
    assert names == {"Parent Rule", "Grand"}
    assert child.parent_workspace == "parent"
    assert all(rule.id not in {"p", "g"} for rule in child.inherited_rules.values())


def test_workspace_manager_save_load_and_corrupt_file(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.create_workspace("Saved", "desc")
    manager.save_workspaces({workspace.id: workspace})

    loaded = manager.load_workspaces()
    assert list(loaded.values())[0].name == "Saved"

    (tmp_path / "workspaces.json").write_text("{ broken", encoding="utf-8")
    assert manager.load_workspaces() == {}


def test_workspace_resolution_and_ensure_workspace_paths(tmp_path):
    manager = WorkspaceManager(tmp_path)
    root = tmp_path / "root"
    root.mkdir()
    workspace = Workspace(id="abcdef123", name="Main", root_path=str(root))
    manager.save_workspaces({workspace.id: workspace})

    workspaces = manager.load_workspaces()
    assert resolve_workspace(workspaces, "abcdef123").name == "Main"
    assert resolve_workspace(workspaces, "abcdef").name == "Main"
    assert resolve_workspace(workspaces, "Main").id == "abcdef123"
    assert resolve_workspace(workspaces, "missing") is None

    resolved_workspace, resolved_root = ensure_workspace(manager, "Main")
    assert resolved_workspace.id == "abcdef123"
    assert resolved_root == root.resolve()
    assert default_workspace_root("x").name == "ws_x"


def test_ensure_workspace_create_init_and_error_paths(tmp_path):
    manager = WorkspaceManager(tmp_path)

    with pytest.raises(ValueError, match="Workspace not found"):
        ensure_workspace(manager, "new")

    created_workspace, created_root = ensure_workspace(
        manager, "new", create_missing=True, init_files=True
    )

    assert created_workspace.name == "new"
    assert created_root.exists()
    assert (created_root / "prompt" / "AGENTS.md").exists()
    stored = json.loads((tmp_path / "workspaces.json").read_text(encoding="utf-8"))
    assert stored[created_workspace.id]["root_path"] == str(created_root)

    no_root = Workspace(id="no-root", name="No Root")
    manager.save_workspaces({"no-root": no_root})
    with pytest.raises(ValueError, match="no root_path"):
        ensure_workspace(manager, "No Root")

    missing_root = Workspace(id="missing-root", name="Missing", root_path=str(tmp_path / "gone"))
    manager.save_workspaces({"missing-root": missing_root})
    with pytest.raises(FileNotFoundError, match="does not exist"):
        ensure_workspace(manager, "Missing")
