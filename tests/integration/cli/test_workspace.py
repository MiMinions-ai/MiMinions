"""
Basic test for workspace functionality.
"""

from miminions.core.workspace import WorkspaceManager, Workspace, Node, Rule, NodeType, RulePriority


def test_workspace_creation(tmp_path):
    """Test basic workspace creation and management."""
    print("Testing workspace creation...")

    manager = WorkspaceManager(tmp_path)

    # Test creating a workspace
    workspace = manager.create_workspace("Test Workspace", "A test workspace")
    assert workspace.name == "Test Workspace", f"expect result to be {'Test Workspace'}, got {workspace.name}"
    assert workspace.description == "A test workspace", f"expect result to be {'A test workspace'}, got {workspace.description}"
    assert len(workspace.nodes) == 0, f"expect result to be {0}, got {len(workspace.nodes)}"
    assert len(workspace.rules) == 0, f"expect result to be {0}, got {len(workspace.rules)}"

    # Test saving and loading
    workspaces = {workspace.id: workspace}
    manager.save_workspaces(workspaces)

    loaded_workspaces = manager.load_workspaces()
    assert len(loaded_workspaces) == 1, f"expect result to be {1}, got {len(loaded_workspaces)}"

    loaded_workspace = list(loaded_workspaces.values())[0]
    assert loaded_workspace.name == workspace.name, f"expect result to be {workspace.name}, got {loaded_workspace.name}"
    assert loaded_workspace.description == workspace.description, f"expect result to be {workspace.description}, got {loaded_workspace.description}"

    print("✓ Workspace creation test passed")


def test_node_management(tmp_path):
    """Test node creation and management within workspace."""
    print("Testing node management...")

    manager = WorkspaceManager(tmp_path)
    workspace = manager.create_workspace("Node Test", "Testing node management")

    # Create nodes
    agent_node = Node(
        name="Test Agent",
        type=NodeType.AGENT,
        properties={"role": "assistant"}
    )

    task_node = Node(
        name="Test Task",
        type=NodeType.TASK,
        properties={"priority": "high"}
    )

    # Add nodes to workspace
    workspace.add_node(agent_node)
    workspace.add_node(task_node)

    assert len(workspace.nodes) == 2, f"expect result to be {2}, got {len(workspace.nodes)}"
    assert agent_node.id in workspace.nodes, f"expect agent_node.id in workspace.nodes, got {agent_node.id}"
    assert task_node.id in workspace.nodes, f"expect task_node.id in workspace.nodes, got {task_node.id}"

    # Test node connections
    connected = workspace.connect_nodes(agent_node.id, task_node.id)
    assert connected is True, f"expect result to be {True}, got {connected}"
    assert task_node.id in workspace.nodes[agent_node.id].connections, f"expect task_node.id in workspace.nodes[agent_node.id].connections, got {task_node.id}"
    assert agent_node.id in workspace.nodes[task_node.id].connections, f"expect agent_node.id in workspace.nodes[task_node.id].connections, got {agent_node.id}"

    # Test network summary
    summary = workspace.get_network_summary()
    assert summary['total_nodes'] == 2, f"expect result to be {2}, got {summary['total_nodes']}"
    assert summary['total_connections'] == 1, f"expect result to be {1}, got {summary['total_connections']}"
    assert 'agent' in summary['node_types'], f"expect workspace network summary node_types includes 'agent', got {summary['node_types']}"
    assert 'task' in summary['node_types'], f"expect workspace network summary node_types includes 'task', got {summary['node_types']}"

    print("✓ Node management test passed")


def test_rule_system():
    """Test rule creation and evaluation."""
    print("Testing rule system...")

    workspace = Workspace(name="Rule Test", description="Testing rule system")

    # Create a rule
    rule = Rule(
        name="Test Rule",
        description="A test rule",
        condition={
            "type": "state_equals",
            "key": "test_key",
            "value": "test_value"
        },
        action={
            "type": "test_action",
            "message": "Rule triggered"
        },
        priority=RulePriority.HIGH
    )

    workspace.add_rule(rule)
    assert len(workspace.rules) == 1, f"expect result to be {1}, got {len(workspace.rules)}"
    assert rule.id in workspace.rules, f"expect rule.id in workspace.rules, got {rule.id}"

    # Test rule evaluation with matching state
    workspace.state = {"test_key": "test_value"}
    actions = workspace.evaluate_state_logic()
    assert len(actions) == 1, f"expect result to be {1}, got {len(actions)}"
    assert actions[0]['rule_name'] == "Test Rule", f"expect result to be {'Test Rule'}, got {actions[0]['rule_name']}"
    assert actions[0]['action']['message'] == "Rule triggered", f"expect result to be {'Rule triggered'}, got {actions[0]['action']['message']}"

    # Test rule evaluation with non-matching state
    workspace.state = {"test_key": "different_value"}
    actions = workspace.evaluate_state_logic()
    assert len(actions) == 0, f"expect result to be {0}, got {len(actions)}"

    print("✓ Rule system test passed")


def test_rule_inheritance():
    """Test rule inheritance between workspaces."""
    print("Testing rule inheritance...")

    # Create parent workspace with rules
    parent_workspace = Workspace(name="Parent", description="Parent workspace")

    parent_rule = Rule(
        name="Parent Rule",
        description="A rule from parent workspace",
        condition={"type": "always"},
        action={"type": "parent_action"},
        priority=RulePriority.MEDIUM
    )

    parent_workspace.add_rule(parent_rule)

    # Create child workspace
    child_workspace = Workspace(name="Child", description="Child workspace")

    # Test inheritance
    child_workspace.inherit_rules_from(parent_workspace)

    assert len(child_workspace.inherited_rules) == 1, f"expect result to be {1}, got {len(child_workspace.inherited_rules)}"
    assert child_workspace.parent_workspace == parent_workspace.id, f"expect result to be {parent_workspace.id}, got {child_workspace.parent_workspace}"

    # Verify inherited rule properties
    inherited_rule = list(child_workspace.inherited_rules.values())[0]
    assert inherited_rule.name == parent_rule.name, f"expect result to be {parent_rule.name}, got {inherited_rule.name}"
    assert inherited_rule.priority == parent_rule.priority, f"expect result to be {parent_rule.priority}, got {inherited_rule.priority}"
    inherited_prefix_is_parent = (inherited_rule.inherited_from or "").startswith("Parent:")
    assert inherited_prefix_is_parent, f"expect inherited rule source to start with 'Parent:', got {inherited_rule.inherited_from}"

    # Test that child can evaluate inherited rules
    actions = child_workspace.evaluate_state_logic()
    assert len(actions) == 1, f"expect result to be {1}, got {len(actions)}"
    assert actions[0]['rule_name'] == "Parent Rule", f"expect result to be {'Parent Rule'}, got {actions[0]['rule_name']}"

    print("✓ Rule inheritance test passed")


def test_sample_workspace(tmp_path):
    """Test sample workspace creation."""
    print("Testing sample workspace...")

    manager = WorkspaceManager(tmp_path)
    workspace = manager.create_sample_workspace()

    # Verify sample workspace has expected components
    assert workspace.name == "Sample Workspace", f"expect result to be {'Sample Workspace'}, got {workspace.name}"
    assert len(workspace.nodes) == 3, f"expect result to be {3}, got {len(workspace.nodes)}"  # agent, task, knowledge
    assert len(workspace.rules) == 2, f"expect result to be {2}, got {len(workspace.rules)}"  # two sample rules
    assert len(workspace.state) > 0, f"expect len(workspace.state) > 0, got {len(workspace.state)}"   # has initial state

    # Verify nodes are connected
    summary = workspace.get_network_summary()
    assert summary['total_connections'] >= 2, f"expect summary['total_connections'] >= 2, got {summary['total_connections']}"  # agent connected to task and knowledge

    # Verify rule evaluation works
    actions = workspace.evaluate_state_logic()
    assert len(actions) > 0, f"expect len(actions) > 0, got {len(actions)}"  # Should have applicable actions

    print("✓ Sample workspace test passed")