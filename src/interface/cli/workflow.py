"""
Workflow management commands for MiMinions CLI.
"""

import click
import json
import uuid
from pathlib import Path
from .auth import get_config_dir, is_authenticated


def get_workflows_file():
    """Get the workflows configuration file path."""
    return get_config_dir() / "workflows.json"


def load_workflows():
    """Load workflows from configuration."""
    workflows_file = get_workflows_file()
    if not workflows_file.exists():
        return {}
    
    with open(workflows_file, "r") as f:
        return json.load(f)


def save_workflows(workflows):
    """Save workflows to configuration."""
    workflows_file = get_workflows_file()
    with open(workflows_file, "w") as f:
        json.dump(workflows, f, indent=2)


def require_auth():
    """Decorator to require authentication."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                click.echo("Please sign in first using 'miminions auth signin'", err=True)
                return
            return f(*args, **kwargs)
        return wrapper
    return decorator


@click.group()
def workflow_cli():
    """Workflow management commands."""
    pass


@workflow_cli.command("list")
@require_auth()
def list_workflows():
    """List all workflows."""
    workflows = load_workflows()
    
    if not workflows:
        click.echo("No workflows configured.")
        return
    
    click.echo("Workflows:")
    for workflow_id, workflow_data in workflows.items():
        status = workflow_data.get("status", "stopped")
        name = workflow_data.get("name", workflow_id)
        description = workflow_data.get("description", "No description")
        agents = workflow_data.get("agents", [])
        click.echo(f"  {workflow_id}: {name} ({status}) - {description} [{len(agents)} agents]")


@workflow_cli.command("add")
@click.option("--name", prompt="Workflow name", help="Name of the workflow")
@click.option("--description", prompt="Description", help="Description of the workflow")
@click.option("--agents", help="Comma-separated list of agent IDs")
@require_auth()
def add_workflow(name, description, agents):
    """Add a new workflow."""
    workflows = load_workflows()
    
    # Generate a unique ID
    workflow_id = str(uuid.uuid4())[:8]
    
    agent_list = []
    if agents:
        agent_list = [agent.strip() for agent in agents.split(",")]
    
    workflows[workflow_id] = {
        "name": name,
        "description": description,
        "agents": agent_list,
        "status": "stopped",
        "tasks": [],
        "created_at": click.get_current_context().meta.get("timestamp", ""),
        "updated_at": None
    }
    
    save_workflows(workflows)
    click.echo(f"Workflow '{name}' added successfully with ID: {workflow_id}")


@workflow_cli.command("update")
@click.argument("workflow_id")
@click.option("--name", help="New name for the workflow")
@click.option("--description", help="New description for the workflow")
@click.option("--agents", help="Comma-separated list of agent IDs")
@require_auth()
def update_workflow(workflow_id, name, description, agents):
    """Update an existing workflow."""
    workflows = load_workflows()
    
    if workflow_id not in workflows:
        click.echo(f"Workflow '{workflow_id}' not found.", err=True)
        return
    
    workflow = workflows[workflow_id]
    
    if name:
        workflow["name"] = name
    if description:
        workflow["description"] = description
    if agents:
        workflow["agents"] = [agent.strip() for agent in agents.split(",")]
    
    workflow["updated_at"] = click.get_current_context().meta.get("timestamp", "")
    
    save_workflows(workflows)
    click.echo(f"Workflow '{workflow_id}' updated successfully")


@workflow_cli.command("remove")
@click.argument("workflow_id")
@click.confirmation_option(prompt="Are you sure you want to remove this workflow?")
@require_auth()
def remove_workflow(workflow_id):
    """Remove a workflow."""
    workflows = load_workflows()
    
    if workflow_id not in workflows:
        click.echo(f"Workflow '{workflow_id}' not found.", err=True)
        return
    
    del workflows[workflow_id]
    save_workflows(workflows)
    click.echo(f"Workflow '{workflow_id}' removed successfully")


@workflow_cli.command("start")
@click.argument("workflow_id")
@require_auth()
def start_workflow(workflow_id):
    """Start a workflow."""
    workflows = load_workflows()
    
    if workflow_id not in workflows:
        click.echo(f"Workflow '{workflow_id}' not found.", err=True)
        return
    
    workflow = workflows[workflow_id]
    
    if workflow["status"] == "running":
        click.echo(f"Workflow '{workflow_id}' is already running.")
        return
    
    if not workflow["agents"]:
        click.echo(f"Workflow '{workflow_id}' has no agents assigned.", err=True)
        return
    
    workflow["status"] = "running"
    workflow["updated_at"] = click.get_current_context().meta.get("timestamp", "")
    
    save_workflows(workflows)
    click.echo(f"Workflow '{workflow_id}' started successfully")


@workflow_cli.command("pause")
@click.argument("workflow_id")
@require_auth()
def pause_workflow(workflow_id):
    """Pause a running workflow."""
    workflows = load_workflows()
    
    if workflow_id not in workflows:
        click.echo(f"Workflow '{workflow_id}' not found.", err=True)
        return
    
    workflow = workflows[workflow_id]
    
    if workflow["status"] != "running":
        click.echo(f"Workflow '{workflow_id}' is not running.")
        return
    
    workflow["status"] = "paused"
    workflow["updated_at"] = click.get_current_context().meta.get("timestamp", "")
    
    save_workflows(workflows)
    click.echo(f"Workflow '{workflow_id}' paused successfully")


@workflow_cli.command("stop")
@click.argument("workflow_id")
@require_auth()
def stop_workflow(workflow_id):
    """Stop a workflow."""
    workflows = load_workflows()
    
    if workflow_id not in workflows:
        click.echo(f"Workflow '{workflow_id}' not found.", err=True)
        return
    
    workflow = workflows[workflow_id]
    
    if workflow["status"] == "stopped":
        click.echo(f"Workflow '{workflow_id}' is already stopped.")
        return
    
    workflow["status"] = "stopped"
    workflow["updated_at"] = click.get_current_context().meta.get("timestamp", "")
    
    save_workflows(workflows)
    click.echo(f"Workflow '{workflow_id}' stopped successfully")


@workflow_cli.command("show")
@click.argument("workflow_id")
@require_auth()
def show_workflow(workflow_id):
    """Show detailed information about a workflow."""
    workflows = load_workflows()
    
    if workflow_id not in workflows:
        click.echo(f"Workflow '{workflow_id}' not found.", err=True)
        return
    
    workflow = workflows[workflow_id]
    
    click.echo(f"Workflow ID: {workflow_id}")
    click.echo(f"Name: {workflow['name']}")
    click.echo(f"Description: {workflow['description']}")
    click.echo(f"Status: {workflow['status']}")
    click.echo(f"Agents: {', '.join(workflow['agents']) if workflow['agents'] else 'None'}")
    click.echo(f"Tasks: {len(workflow['tasks'])}")
    click.echo(f"Created: {workflow['created_at']}")
    if workflow.get('updated_at'):
        click.echo(f"Updated: {workflow['updated_at']}")