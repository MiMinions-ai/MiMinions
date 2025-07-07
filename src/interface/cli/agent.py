"""
Agent management commands for MiMinions CLI.
"""

import click
import json
from pathlib import Path
from .auth import get_config_dir, is_authenticated


def get_agents_file():
    """Get the agents configuration file path."""
    return get_config_dir() / "agents.json"


def load_agents():
    """Load agents from configuration."""
    agents_file = get_agents_file()
    if not agents_file.exists():
        return {}
    
    with open(agents_file, "r") as f:
        return json.load(f)


def save_agents(agents):
    """Save agents to configuration."""
    agents_file = get_agents_file()
    with open(agents_file, "w") as f:
        json.dump(agents, f, indent=2)


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
def agent_cli():
    """Agent management commands."""
    pass


@agent_cli.command("list")
@require_auth()
def list_agents():
    """List all agents."""
    agents = load_agents()
    
    if not agents:
        click.echo("No agents configured.")
        return
    
    click.echo("Agents:")
    for agent_id, agent_data in agents.items():
        status = agent_data.get("status", "inactive")
        name = agent_data.get("name", agent_id)
        description = agent_data.get("description", "No description")
        click.echo(f"  {agent_id}: {name} ({status}) - {description}")


@agent_cli.command("add")
@click.option("--name", prompt="Agent name", help="Name of the agent")
@click.option("--description", prompt="Description", help="Description of the agent")
@click.option("--type", prompt="Agent type", help="Type of agent")
@require_auth()
def add_agent(name, description, type):
    """Add a new agent."""
    agents = load_agents()
    
    # Generate a simple ID based on name
    agent_id = name.lower().replace(" ", "_")
    
    if agent_id in agents:
        click.echo(f"Agent '{agent_id}' already exists.", err=True)
        return
    
    agents[agent_id] = {
        "name": name,
        "description": description,
        "type": type,
        "status": "inactive",
        "goal": None,
        "created_at": click.get_current_context().meta.get("timestamp", "")
    }
    
    save_agents(agents)
    click.echo(f"Agent '{name}' added successfully with ID: {agent_id}")


@agent_cli.command("update")
@click.argument("agent_id")
@click.option("--name", help="New name for the agent")
@click.option("--description", help="New description for the agent")
@click.option("--type", help="New type for the agent")
@require_auth()
def update_agent(agent_id, name, description, type):
    """Update an existing agent."""
    agents = load_agents()
    
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return
    
    agent = agents[agent_id]
    
    if name:
        agent["name"] = name
    if description:
        agent["description"] = description
    if type:
        agent["type"] = type
    
    save_agents(agents)
    click.echo(f"Agent '{agent_id}' updated successfully")


@agent_cli.command("remove")
@click.argument("agent_id")
@click.confirmation_option(prompt="Are you sure you want to remove this agent?")
@require_auth()
def remove_agent(agent_id):
    """Remove an agent."""
    agents = load_agents()
    
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return
    
    del agents[agent_id]
    save_agents(agents)
    click.echo(f"Agent '{agent_id}' removed successfully")


@agent_cli.command("set-goal")
@click.argument("agent_id")
@click.option("--goal", prompt="Goal", help="Goal for the agent")
@require_auth()
def set_goal(agent_id, goal):
    """Set a goal for an agent."""
    agents = load_agents()
    
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return
    
    agents[agent_id]["goal"] = goal
    save_agents(agents)
    click.echo(f"Goal set for agent '{agent_id}': {goal}")


@agent_cli.command("run")
@click.argument("agent_id")
@click.option("--async", "async_run", is_flag=True, help="Run agent asynchronously")
@require_auth()
def run_agent(agent_id, async_run):
    """Run an agent."""
    agents = load_agents()
    
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return
    
    agent = agents[agent_id]
    
    if not agent.get("goal"):
        click.echo(f"Agent '{agent_id}' has no goal set. Use 'set-goal' command first.", err=True)
        return
    
    # Update status
    agents[agent_id]["status"] = "running"
    save_agents(agents)
    
    if async_run:
        click.echo(f"Agent '{agent_id}' started asynchronously")
    else:
        click.echo(f"Running agent '{agent_id}' with goal: {agent['goal']}")
        # In a real implementation, this would execute the agent
        click.echo("Agent execution completed")