"""
Workspace management commands for MiMinions CLI.
"""

import click
import json
from pathlib import Path
from .auth import get_config_dir, is_authenticated, is_public_access_enabled

# Import workspace module - handle path correctly
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from miminions.core.workspace import WorkspaceManager, Workspace, Node, Rule, NodeType, RulePriority


def require_auth():
    """Decorator to require authentication or allow public access."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                if is_public_access_enabled():
                    # Show warning but allow access
                    click.echo("⚠️  Running in public access mode. Sign in for full functionality.", err=True)
                else:
                    # Require authentication
                    click.echo("Please sign in first using 'miminions auth signin'", err=True)
                    return
            return f(*args, **kwargs)
        return wrapper
    return decorator


def get_workspace_manager():
    """Get the workspace manager instance."""
    return WorkspaceManager(get_config_dir())


@click.group()
def workspace_cli():
    """Workspace management commands."""
    pass


@workspace_cli.command("list")
@require_auth()
def list_workspaces():
    """List all workspaces."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    if not workspaces:
        click.echo("No workspaces configured.")
        return
    
    click.echo("Workspaces:")
    for workspace_id, workspace in workspaces.items():
        summary = workspace.get_network_summary()
        click.echo(f"  {workspace.name} ({workspace_id[:8]}...)")
        click.echo(f"    Description: {workspace.description or 'No description'}")
        click.echo(f"    Nodes: {summary['total_nodes']}, Rules: {summary['total_rules']}, " +
                  f"Inherited Rules: {summary['inherited_rules']}")
        click.echo(f"    Created: {workspace.created_at}")
        click.echo()


@workspace_cli.command("add")
@click.option("--name", required=True, help="Workspace name")
@click.option("--description", default="", help="Workspace description")
@click.option("--sample", is_flag=True, help="Create a sample workspace with example nodes and rules")
@require_auth()
def add_workspace(name, description, sample):
    """Add a new workspace."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    # Check if workspace name already exists
    for workspace in workspaces.values():
        if workspace.name == name:
            click.echo(f"A workspace named '{name}' already exists.")
            return
    
    if sample:
        workspace = manager.create_sample_workspace()
        workspace.name = name
        if description:
            workspace.description = description
    else:
        workspace = manager.create_workspace(name, description)
    
    workspaces[workspace.id] = workspace
    manager.save_workspaces(workspaces)
    
    if sample:
        click.echo(f"Sample workspace '{name}' created successfully with ID: {workspace.id}")
        click.echo("The sample workspace includes example nodes, rules, and state logic.")
    else:
        click.echo(f"Workspace '{name}' created successfully with ID: {workspace.id}")


@workspace_cli.command("show")
@click.argument("workspace_id")
@require_auth()
def show_workspace(workspace_id):
    """Show workspace details."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    # Find workspace by ID or name
    workspace = None
    for ws_id, ws in workspaces.items():
        if ws_id.startswith(workspace_id) or ws.name == workspace_id:
            workspace = ws
            break
    
    if not workspace:
        click.echo(f"Workspace '{workspace_id}' not found.")
        return
    
    click.echo(f"Workspace: {workspace.name}")
    click.echo(f"ID: {workspace.id}")
    click.echo(f"Description: {workspace.description or 'No description'}")
    
    if workspace.parent_workspace:
        click.echo(f"Parent Workspace: {workspace.parent_workspace}")
    
    click.echo(f"Created: {workspace.created_at}")
    click.echo(f"Updated: {workspace.updated_at}")
    click.echo()
    
    # Show network summary
    summary = workspace.get_network_summary()
    click.echo("Network Summary:")
    click.echo(f"  Total Nodes: {summary['total_nodes']}")
    click.echo(f"  Node Types: {summary['node_types']}")
    click.echo(f"  Total Connections: {summary['total_connections']}")
    click.echo(f"  Total Rules: {summary['total_rules']}")
    click.echo(f"  Inherited Rules: {summary['inherited_rules']}")
    click.echo()
    
    # Show nodes
    if workspace.nodes:
        click.echo("Nodes:")
        for node in workspace.nodes.values():
            click.echo(f"  {node.name} ({node.id[:8]}...)")
            click.echo(f"    Type: {node.type.value}")
            click.echo(f"    Connections: {len(node.connections)}")
            if node.properties:
                click.echo(f"    Properties: {json.dumps(node.properties, indent=6)[1:-1]}")
            if node.state:
                click.echo(f"    State: {json.dumps(node.state, indent=6)[1:-1]}")
            click.echo()
    
    # Show rules
    if workspace.rules:
        click.echo("Workspace Rules:")
        for rule in workspace.rules.values():
            click.echo(f"  {rule.name} ({rule.id[:8]}...)")
            click.echo(f"    Priority: {rule.priority.name}")
            click.echo(f"    Description: {rule.description}")
            click.echo(f"    Enabled: {rule.enabled}")
            click.echo()
    
    # Show inherited rules
    if workspace.inherited_rules:
        click.echo("Inherited Rules:")
        for rule in workspace.inherited_rules.values():
            click.echo(f"  {rule.name} ({rule.id[:8]}...)")
            click.echo(f"    Priority: {rule.priority.name}")
            click.echo(f"    Inherited from: {rule.inherited_from}")
            click.echo(f"    Enabled: {rule.enabled}")
            click.echo()
    
    # Show current state
    if workspace.state:
        click.echo("Current State:")
        for key, value in workspace.state.items():
            click.echo(f"  {key}: {value}")
        click.echo()


@workspace_cli.command("update")
@click.argument("workspace_id")
@click.option("--name", help="New workspace name")
@click.option("--description", help="New workspace description")
@require_auth()
def update_workspace(workspace_id, name, description):
    """Update workspace details."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    # Find workspace by ID or name
    workspace = None
    for ws_id, ws in workspaces.items():
        if ws_id.startswith(workspace_id) or ws.name == workspace_id:
            workspace = ws
            break
    
    if not workspace:
        click.echo(f"Workspace '{workspace_id}' not found.")
        return
    
    if name:
        # Check if new name already exists
        for other_ws in workspaces.values():
            if other_ws.id != workspace.id and other_ws.name == name:
                click.echo(f"A workspace named '{name}' already exists.")
                return
        workspace.name = name
    
    if description is not None:
        workspace.description = description
    
    from datetime import datetime
    workspace.updated_at = datetime.utcnow().isoformat()
    
    manager.save_workspaces(workspaces)
    click.echo(f"Workspace updated successfully.")


@workspace_cli.command("remove")
@click.argument("workspace_id")
@click.option("--force", is_flag=True, help="Force removal without confirmation")
@require_auth()
def remove_workspace(workspace_id, force):
    """Remove a workspace."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    # Find workspace by ID or name
    workspace = None
    workspace_key = None
    for ws_id, ws in workspaces.items():
        if ws_id.startswith(workspace_id) or ws.name == workspace_id:
            workspace = ws
            workspace_key = ws_id
            break
    
    if not workspace:
        click.echo(f"Workspace '{workspace_id}' not found.")
        return
    
    if not force:
        click.confirm(f"Are you sure you want to remove workspace '{workspace.name}'?", abort=True)
    
    del workspaces[workspace_key]
    manager.save_workspaces(workspaces)
    
    click.echo(f"Workspace '{workspace.name}' removed successfully.")


@workspace_cli.command("evaluate")
@click.argument("workspace_id")
@require_auth()
def evaluate_workspace(workspace_id):
    """Evaluate workspace state logic and show applicable actions."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    # Find workspace by ID or name
    workspace = None
    for ws_id, ws in workspaces.items():
        if ws_id.startswith(workspace_id) or ws.name == workspace_id:
            workspace = ws
            break
    
    if not workspace:
        click.echo(f"Workspace '{workspace_id}' not found.")
        return
    
    click.echo(f"Evaluating workspace: {workspace.name}")
    click.echo()
    
    # Show current state
    if workspace.state:
        click.echo("Current State:")
        for key, value in workspace.state.items():
            click.echo(f"  {key}: {value}")
        click.echo()
    
    # Evaluate state logic
    actions = workspace.evaluate_state_logic()
    
    if not actions:
        click.echo("No applicable actions based on current state and rules.")
        return
    
    click.echo("Applicable Actions:")
    for i, action in enumerate(actions, 1):
        click.echo(f"{i}. {action['rule_name']} (Priority: {action['priority']})")
        if action['inherited_from']:
            click.echo(f"   Inherited from: {action['inherited_from']}")
        click.echo(f"   Action: {json.dumps(action['action'], indent=4)}")
        click.echo()


@workspace_cli.command("add-node")
@click.argument("workspace_id")
@click.option("--name", required=True, help="Node name")
@click.option("--type", "node_type", type=click.Choice(['agent', 'task', 'workflow', 'knowledge', 'custom']), 
              default='custom', help="Node type")
@click.option("--properties", help="Node properties as JSON string")
@require_auth()
def add_node(workspace_id, name, node_type, properties):
    """Add a node to a workspace."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    # Find workspace
    workspace = None
    workspace_key = None
    for ws_id, ws in workspaces.items():
        if ws_id.startswith(workspace_id) or ws.name == workspace_id:
            workspace = ws
            workspace_key = ws_id
            break
    
    if not workspace:
        click.echo(f"Workspace '{workspace_id}' not found.")
        return
    
    # Parse properties
    node_properties = {}
    if properties:
        try:
            node_properties = json.loads(properties)
        except json.JSONDecodeError:
            click.echo("Invalid JSON format for properties.")
            return
    
    # Create node
    node = Node(
        name=name,
        type=NodeType(node_type),
        properties=node_properties
    )
    
    workspace.add_node(node)
    manager.save_workspaces(workspaces)
    
    click.echo(f"Node '{name}' added to workspace '{workspace.name}' with ID: {node.id}")


@workspace_cli.command("connect-nodes")
@click.argument("workspace_id")
@click.argument("node1_id")
@click.argument("node2_id")
@require_auth()
def connect_nodes(workspace_id, node1_id, node2_id):
    """Connect two nodes in a workspace."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    # Find workspace
    workspace = None
    workspace_key = None
    for ws_id, ws in workspaces.items():
        if ws_id.startswith(workspace_id) or ws.name == workspace_id:
            workspace = ws
            workspace_key = ws_id
            break
    
    if not workspace:
        click.echo(f"Workspace '{workspace_id}' not found.")
        return
    
    # Find nodes (support partial ID matching)
    node1 = None
    node2 = None
    
    for node_id, node in workspace.nodes.items():
        if node_id.startswith(node1_id) or node.name == node1_id:
            node1 = node
        if node_id.startswith(node2_id) or node.name == node2_id:
            node2 = node
    
    if not node1:
        click.echo(f"Node '{node1_id}' not found in workspace.")
        return
    
    if not node2:
        click.echo(f"Node '{node2_id}' not found in workspace.")
        return
    
    if workspace.connect_nodes(node1.id, node2.id):
        manager.save_workspaces(workspaces)
        click.echo(f"Connected nodes '{node1.name}' and '{node2.name}'.")
    else:
        click.echo("Failed to connect nodes.")


@workspace_cli.command("set-state")
@click.argument("workspace_id")
@click.option("--key", required=True, help="State key")
@click.option("--value", required=True, help="State value")
@require_auth()
def set_state(workspace_id, key, value):
    """Set a state value in the workspace."""
    manager = get_workspace_manager()
    workspaces = manager.load_workspaces()
    
    # Find workspace
    workspace = None
    workspace_key = None
    for ws_id, ws in workspaces.items():
        if ws_id.startswith(workspace_id) or ws.name == workspace_id:
            workspace = ws
            workspace_key = ws_id
            break
    
    if not workspace:
        click.echo(f"Workspace '{workspace_id}' not found.")
        return
    
    # Try to parse value as JSON, fallback to string
    try:
        parsed_value = json.loads(value)
    except json.JSONDecodeError:
        parsed_value = value
    
    workspace.state[key] = parsed_value
    
    from datetime import datetime
    workspace.updated_at = datetime.utcnow().isoformat()
    
    manager.save_workspaces(workspaces)
    click.echo(f"Set state '{key}' = '{parsed_value}' in workspace '{workspace.name}'.")