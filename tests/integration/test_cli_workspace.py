"""
Basic test for workspace functionality.
"""

import sys
import os
import tempfile
import shutil
from pathlib import Path

# Add src to path so we can import modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))

from miminions.core.workspace import WorkspaceManager, Workspace, Node, Rule, NodeType, RulePriority


def test_workspace_creation():
    """Test basic workspace creation and management."""
    print("Testing workspace creation...")
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir)
    
    try:
        manager = WorkspaceManager(config_dir)
        
        # Test creating a workspace
        workspace = manager.create_workspace("Test Workspace", "A test workspace")
        assert workspace.name == "Test Workspace"
        assert workspace.description == "A test workspace"
        assert len(workspace.nodes) == 0
        assert len(workspace.rules) == 0
        
        # Test saving and loading
        workspaces = {workspace.id: workspace}
        manager.save_workspaces(workspaces)
        
        loaded_workspaces = manager.load_workspaces()
        assert len(loaded_workspaces) == 1
        
        loaded_workspace = list(loaded_workspaces.values())[0]
        assert loaded_workspace.name == workspace.name
        assert loaded_workspace.description == workspace.description
        
        print("✓ Workspace creation test passed")
        return True
        
    except Exception as e:
        print(f"✗ Workspace creation test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_node_management():
    """Test node creation and management within workspace."""
    print("Testing node management...")
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir)
    
    try:
        manager = WorkspaceManager(config_dir)
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
        
        assert len(workspace.nodes) == 2
        assert agent_node.id in workspace.nodes
        assert task_node.id in workspace.nodes
        
        # Test node connections
        assert workspace.connect_nodes(agent_node.id, task_node.id) == True
        assert task_node.id in workspace.nodes[agent_node.id].connections
        assert agent_node.id in workspace.nodes[task_node.id].connections
        
        # Test network summary
        summary = workspace.get_network_summary()
        assert summary['total_nodes'] == 2
        assert summary['total_connections'] == 1
        assert 'agent' in summary['node_types']
        assert 'task' in summary['node_types']
        
        print("✓ Node management test passed")
        return True
        
    except Exception as e:
        print(f"✗ Node management test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir)


def test_rule_system():
    """Test rule creation and evaluation."""
    print("Testing rule system...")
    
    try:
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
        assert len(workspace.rules) == 1
        assert rule.id in workspace.rules
        
        # Test rule evaluation with matching state
        workspace.state = {"test_key": "test_value"}
        actions = workspace.evaluate_state_logic()
        assert len(actions) == 1
        assert actions[0]['rule_name'] == "Test Rule"
        assert actions[0]['action']['message'] == "Rule triggered"
        
        # Test rule evaluation with non-matching state
        workspace.state = {"test_key": "different_value"}
        actions = workspace.evaluate_state_logic()
        assert len(actions) == 0
        
        print("✓ Rule system test passed")
        return True
        
    except Exception as e:
        print(f"✗ Rule system test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_rule_inheritance():
    """Test rule inheritance between workspaces."""
    print("Testing rule inheritance...")
    
    try:
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
        
        assert len(child_workspace.inherited_rules) == 1
        assert child_workspace.parent_workspace == parent_workspace.id
        
        # Verify inherited rule properties
        inherited_rule = list(child_workspace.inherited_rules.values())[0]
        assert inherited_rule.name == parent_rule.name
        assert inherited_rule.priority == parent_rule.priority
        assert inherited_rule.inherited_from.startswith("Parent:")
        
        # Test that child can evaluate inherited rules
        actions = child_workspace.evaluate_state_logic()
        assert len(actions) == 1
        assert actions[0]['rule_name'] == "Parent Rule"
        
        print("✓ Rule inheritance test passed")
        return True
        
    except Exception as e:
        print(f"✗ Rule inheritance test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_sample_workspace():
    """Test sample workspace creation."""
    print("Testing sample workspace...")
    
    # Create temporary directory for testing
    temp_dir = tempfile.mkdtemp()
    config_dir = Path(temp_dir)
    
    try:
        manager = WorkspaceManager(config_dir)
        workspace = manager.create_sample_workspace()
        
        # Verify sample workspace has expected components
        assert workspace.name == "Sample Workspace"
        assert len(workspace.nodes) == 3  # agent, task, knowledge
        assert len(workspace.rules) == 2  # two sample rules
        assert len(workspace.state) > 0   # has initial state
        
        # Verify nodes are connected
        summary = workspace.get_network_summary()
        assert summary['total_connections'] >= 2  # agent connected to task and knowledge
        
        # Verify rule evaluation works
        actions = workspace.evaluate_state_logic()
        assert len(actions) > 0  # Should have applicable actions
        
        print("✓ Sample workspace test passed")
        return True
        
    except Exception as e:
        print(f"✗ Sample workspace test failed: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        shutil.rmtree(temp_dir)


def main():
    """Run all workspace tests."""
    print("Running workspace tests...")
    
    tests = [
        ("Workspace Creation", test_workspace_creation),
        ("Node Management", test_node_management),
        ("Rule System", test_rule_system),
        ("Rule Inheritance", test_rule_inheritance),
        ("Sample Workspace", test_sample_workspace)
    ]
    
    passed = 0
    failed = 0
    
    for test_name, test_func in tests:
        print(f"\n--- Running {test_name} Test ---")
        if test_func():
            passed += 1
        else:
            failed += 1
    
    print(f"\n--- Test Results ---")
    print(f"Passed: {passed}")
    print(f"Failed: {failed}")
    
    return failed == 0


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)