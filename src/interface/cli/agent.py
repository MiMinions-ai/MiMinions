"""
Agent management commands for MiMinions CLI.
"""

import click
from .common import cli_config, cli_utils, require_auth


@click.group()
def agent_cli():
    """Agent management commands."""
    pass


@agent_cli.command("list")
@require_auth()
def list_agents():
    """List all agents."""
    agents = cli_config.load_agents()
    
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
    agents = cli_config.load_agents()
    
    # Generate a simple ID based on name
    agent_id = cli_utils.generate_id(name)
    
    if agent_id in agents:
        click.echo(f"Agent '{agent_id}' already exists.", err=True)
        return
    
    agents[agent_id] = {
        "name": name,
        "description": description,
        "type": type,
        "status": "inactive",
        "goal": None,
        "created_at": cli_utils.format_timestamp()
    }
    
    cli_config.save_agents(agents)
    click.echo(f"Agent '{name}' added successfully with ID: {agent_id}")


@agent_cli.command("update")
@click.argument("agent_id")
@click.option("--name", help="New name for the agent")
@click.option("--description", help="New description for the agent")
@click.option("--type", help="New type for the agent")
@require_auth()
def update_agent(agent_id, name, description, type):
    """Update an existing agent."""
    agents = cli_config.load_agents()
    
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
    
    cli_config.save_agents(agents)
    click.echo(f"Agent '{agent_id}' updated successfully")


@agent_cli.command("remove")
@click.argument("agent_id")
@click.confirmation_option(prompt="Are you sure you want to remove this agent?")
@require_auth()
def remove_agent(agent_id):
    """Remove an agent."""
    agents = cli_config.load_agents()
    
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return
    
    del agents[agent_id]
    cli_config.save_agents(agents)
    click.echo(f"Agent '{agent_id}' removed successfully")


@agent_cli.command("set-goal")
@click.argument("agent_id")
@click.option("--goal", prompt="Goal", help="Goal for the agent")
@require_auth()
def set_goal(agent_id, goal):
    """Set a goal for an agent."""
    agents = cli_config.load_agents()
    
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return
    
    agents[agent_id]["goal"] = goal
    cli_config.save_agents(agents)
    click.echo(f"Goal set for agent '{agent_id}': {goal}")


@agent_cli.command("run")
@click.argument("agent_id")
@click.option("--async", "async_run", is_flag=True, help="Run agent asynchronously")
@require_auth()
def run_agent(agent_id, async_run):
    """Run an agent."""
    agents = cli_config.load_agents()
    
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return
    
    agent = agents[agent_id]
    
    if not agent.get("goal"):
        click.echo(f"Agent '{agent_id}' has no goal set. Use 'set-goal' command first.", err=True)
        return
    
    # Update status
    agents[agent_id]["status"] = "running"
    cli_config.save_agents(agents)
    
    if async_run:
        click.echo(f"Agent '{agent_id}' started asynchronously")
    else:
        click.echo(f"Running agent '{agent_id}' with goal: {agent['goal']}")
        # In a real implementation, this would execute the agent
        click.echo("Agent execution completed")