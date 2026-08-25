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

    assert restored.id == "w1", f"expect workspace id is preserved after workspace serialization round-trip as 'w1', got {restored.id}"
    assert restored.nodes["n1"].type is NodeType.AGENT, f"expect node type is preserved as NodeType.AGENT after workspace serialization round-trip as {NodeType.AGENT}, got {restored.nodes['n1'].type}"
    assert restored.rules["r1"].priority is RulePriority.CRITICAL, f"expect rule priority is preserved as RulePriority.CRITICAL after workspace serialization round-trip as {RulePriority.CRITICAL}, got {restored.rules['r1'].priority}"


def test_node_connections_are_bidirectional_and_removed_cleanly():
    workspace = Workspace(name="Graph")
    first = Node(id="a", name="A")
    second = Node(id="b", name="B")
    workspace.add_node(first)
    workspace.add_node(second)

    connected = workspace.connect_nodes("a", "b")
    assert connected is True, f"expect connect_nodes('a', 'b') returns True, got {connected}"
    missing_connect = workspace.connect_nodes("a", "missing")
    assert missing_connect is False, f"expect connect_nodes('a', 'missing') returns False, got {missing_connect}"
    assert first.connections == ["b"], f"expect ['b'], got {first.connections}"
    assert second.connections == ["a"], f"expect ['a'], got {second.connections}"
    total_connections = workspace.get_network_summary()["total_connections"]
    assert total_connections == 1, f"expect result to be {1}, got {total_connections}"

    disconnected = workspace.disconnect_nodes("a", "b")
    assert disconnected is True, f"expect disconnect_nodes('a', 'b') returns True, got {disconnected}"
    assert first.connections == [], f"expect [] as [], got {first.connections}"
    assert second.connections == [], f"expect [] as [], got {second.connections}"
    disconnected_again = workspace.disconnect_nodes("a", "b")
    assert disconnected_again is False, f"expect disconnect_nodes('a', 'b') returns False when already disconnected, got {disconnected_again}"

    workspace.connect_nodes("a", "b")
    removed = workspace.remove_node("b")
    assert removed is True, f"expect remove_node('b') returns True, got {removed}"
    assert "b" not in workspace.nodes, f"expect not contains 'b', got {workspace.nodes}"
    assert first.connections == [], f"expect [] as [], got {first.connections}"
    missing_removed = workspace.remove_node("missing")
    assert missing_removed is False, f"expect remove_node('missing') returns False, got {missing_removed}"


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

    sorted_rule_ids = [rule.id for rule in workspace.get_all_rules()]
    assert sorted_rule_ids == ["high", "low"], f"expect ['high', 'low'], got {sorted_rule_ids}"
    evaluated_rule_ids = [action["rule_id"] for action in workspace.evaluate_state_logic()]
    assert evaluated_rule_ids == [
        "high",
        "low",
    ], f"expect ['high', 'low'], got {evaluated_rule_ids}"

    always_match = workspace._evaluate_condition({"type": "always"})
    assert always_match is True, f"expect _evaluate_condition(always) returns True, got {always_match}"
    state_equals_match = workspace._evaluate_condition({"type": "state_equals", "key": "count", "value": 2})
    assert state_equals_match is True, f"expect _evaluate_condition(state_equals count=2) returns True, got {state_equals_match}"
    node_count_gte = workspace._evaluate_condition({"type": "node_count", "operator": ">=", "count": 1})
    assert node_count_gte is True, f"expect _evaluate_condition(node_count >= 1) returns True, got {node_count_gte}"
    node_count_lte = workspace._evaluate_condition({"type": "node_count", "operator": "<=", "count": 1})
    assert node_count_lte is True, f"expect _evaluate_condition(node_count <= 1) returns True, got {node_count_lte}"
    node_count_eq = workspace._evaluate_condition({"type": "node_count", "operator": "==", "count": 1})
    assert node_count_eq is True, f"expect _evaluate_condition(node_count == 1) returns True, got {node_count_eq}"
    node_count_gt = workspace._evaluate_condition({"type": "node_count", "operator": ">", "count": 0})
    assert node_count_gt is True, f"expect _evaluate_condition(node_count > 0) returns True, got {node_count_gt}"
    node_count_lt = workspace._evaluate_condition({"type": "node_count", "operator": "<", "count": 2})
    assert node_count_lt is True, f"expect _evaluate_condition(node_count < 2) returns True, got {node_count_lt}"
    node_type_exists = workspace._evaluate_condition({"type": "node_type_exists", "node_type": "agent"})
    assert node_type_exists is True, f"expect _evaluate_condition(node_type_exists agent) returns True, got {node_type_exists}"
    unknown_condition = workspace._evaluate_condition({"type": "unknown"})
    assert unknown_condition is False, f"expect _evaluate_condition(unknown) returns False, got {unknown_condition}"


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
    assert names == {"Parent Rule", "Grand"}, f"expect {{'Parent Rule', 'Grand'}}, got {names}"
    assert child.parent_workspace == "parent", f"expect child workspace records inherited parent workspace id as 'parent', got {child.parent_workspace}"
    inherited_ids = [rule.id for rule in child.inherited_rules.values()]
    assert all(rule_id not in {"p", "g"} for rule_id in inherited_ids), f"expect inherited rule ids are copied and do not contain originals 'p' or 'g', got {inherited_ids}"


def test_workspace_manager_save_load_and_corrupt_file(tmp_path):
    manager = WorkspaceManager(tmp_path)
    workspace = manager.create_workspace("Saved", "desc")
    manager.save_workspaces({workspace.id: workspace})

    loaded = manager.load_workspaces()
    loaded_workspace_name = next(iter(loaded.values())).name
    assert loaded_workspace_name == "Saved", f"expect loaded workspace name matches saved workspace name as 'Saved', got {loaded_workspace_name}"

    (tmp_path / "workspaces.json").write_text("{ broken", encoding="utf-8")
    reloaded = manager.load_workspaces()
    assert reloaded == {}, f"expect result to be {{}}, got {reloaded}"


def test_workspace_resolution_and_ensure_workspace_paths(tmp_path):
    manager = WorkspaceManager(tmp_path)
    root = tmp_path / "root"
    root.mkdir()
    workspace = Workspace(id="abcdef123", name="Main", root_path=str(root))
    manager.save_workspaces({workspace.id: workspace})

    workspaces = manager.load_workspaces()
    resolved = resolve_workspace(workspaces, "abcdef123")
    assert resolved.name == "Main", f"expect resolve_workspace finds workspace by full id and returns workspace name 'Main', got {resolved.name}"
    resolved = resolve_workspace(workspaces, "abcdef")
    assert resolved.name == "Main", f"expect resolve_workspace finds workspace by id prefix and returns workspace name 'Main', got {resolved.name}"
    resolved = resolve_workspace(workspaces, "Main")
    assert resolved.id == "abcdef123", f"expect resolve_workspace finds workspace by name and returns id 'abcdef123', got {resolved.id}"
    resolved = resolve_workspace(workspaces, "missing")
    assert resolved is None, f"expect resolve_workspace returns None for missing lookup key, got {resolved}"

    resolved_workspace, resolved_root = ensure_workspace(manager, "Main")
    assert resolved_workspace.id == "abcdef123", f"expect ensure_workspace resolves existing workspace id 'abcdef123' for workspace name 'Main', got {resolved_workspace.id}"
    assert resolved_root == root.resolve(), f"expect ensure_workspace returns resolved filesystem root for existing workspace as {root.resolve()}, got {resolved_root}"
    default_root = default_workspace_root("x")
    assert default_root.name == "ws_x", f"expect default_workspace_root generates directory name 'ws_x' from workspace id suffix, got {default_root.name}"


def test_ensure_workspace_create_init_and_error_paths(tmp_path):
    manager = WorkspaceManager(tmp_path)

    with pytest.raises(ValueError, match="Workspace not found"):
        ensure_workspace(manager, "new")

    created_workspace, created_root = ensure_workspace(
        manager, "new", create_missing=True, init_files=True
    )

    assert created_workspace.name == "new", f"expect ensure_workspace(create_missing=True) creates workspace named 'new', got {created_workspace.name}"
    root_exists = created_root.exists()
    assert root_exists, f"expect ensure_workspace(create_missing=True) creates workspace root directory, got {root_exists}"
    agents_file_exists = (created_root / "prompt" / "AGENTS.md").exists()
    assert agents_file_exists, f"expect ensure_workspace(init_files=True) creates prompt/AGENTS.md, got {agents_file_exists}"
    stored = json.loads((tmp_path / "workspaces.json").read_text(encoding="utf-8"))
    assert stored[created_workspace.id]["root_path"] == str(created_root), f"expect ensure_workspace persists created workspace root_path to workspaces.json as {created_root!s}, got {stored[created_workspace.id]['root_path']}"

    no_root = Workspace(id="no-root", name="No Root")
    manager.save_workspaces({"no-root": no_root})
    with pytest.raises(ValueError, match="no root_path"):
        ensure_workspace(manager, "No Root")

    missing_root = Workspace(id="missing-root", name="Missing", root_path=str(tmp_path / "gone"))
    manager.save_workspaces({"missing-root": missing_root})
    with pytest.raises(FileNotFoundError, match="does not exist"):
        ensure_workspace(manager, "Missing")
