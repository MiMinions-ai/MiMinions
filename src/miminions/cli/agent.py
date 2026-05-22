"""
Agent management commands for MiMinions CLI.
"""

import click
import json
import re
from datetime import datetime, timezone
from .auth import get_config_dir, is_authenticated, is_public_access_enabled
from miminions.agent import create_minion


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


def _build_cli_extension_agent(agent_data):
    """Create a CLI extension Minion from persisted CLI agent settings."""
    name = agent_data.get("name", "Unnamed Agent")
    base_description = agent_data.get("description", "")
    cli_description = (
        "CLI extension of the core Minion runtime. "
        "Inherit default runtime behavior first; CLI-specific behavior is additive."
    )
    description = f"{base_description}\n\n{cli_description}" if base_description else cli_description
    runtime_agent = create_minion(name=name, description=description)
    _register_default_cli_tools(runtime_agent)
    return runtime_agent


def _register_default_cli_tools(runtime_agent):
    """Register a minimal default CLI toolset on top of the core runtime."""

    def cli_echo(text: str) -> str:
        return text

    def cli_add(a: int, b: int) -> int:
        return a + b

    def cli_now_utc() -> str:
        return datetime.now(timezone.utc).isoformat()

    runtime_agent.register_tool("cli_echo", "Echo input text", cli_echo)
    runtime_agent.register_tool("cli_add", "Add two integers", cli_add)
    runtime_agent.register_tool("cli_now_utc", "Get current UTC timestamp", cli_now_utc)


def _get_agent_record_or_error(agent_id):
    """Load one persisted CLI agent record by id with user-facing errors."""
    agents = load_agents()
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return None
    return agents[agent_id]


def _extract_first_two_ints(text):
    """Extract first two integers from text for simple arithmetic routing."""
    values = [int(v) for v in re.findall(r"-?\d+", text)]
    if len(values) >= 2:
        return values[0], values[1]
    return None


def _execute_prompt_with_tool_fallback(runtime_agent, prompt):
    """Run prompt via model, then fallback to deterministic tool routing if needed."""
    lower = prompt.lower()

    if "add" in lower or "sum" in lower or "plus" in lower:
        pair = _extract_first_two_ints(prompt)
        if pair:
            tool_result = runtime_agent.execute("cli_add", arguments={"a": pair[0], "b": pair[1]})
            if tool_result.error:
                return f"Tool error: {tool_result.error}"
            return f"Used tool cli_add -> {tool_result.result}"

    if "time" in lower or "utc" in lower or "now" in lower:
        tool_result = runtime_agent.execute("cli_now_utc")
        if tool_result.error:
            return f"Tool error: {tool_result.error}"
        return f"Used tool cli_now_utc -> {tool_result.result}"

    if lower.startswith("echo "):
        payload = prompt[5:]
        tool_result = runtime_agent.execute("cli_echo", arguments={"text": payload})
        if tool_result.error:
            return f"Tool error: {tool_result.error}"
        return f"Used tool cli_echo -> {tool_result.result}"

    import asyncio
    output = asyncio.run(runtime_agent.run(prompt))

    return output


# TODO: require_auth disabled until auth is fully implemented
# and the public-access path is clear to users.
# def require_auth():
#     """Decorator to require authentication or allow public access."""
#     def decorator(f):
#         def wrapper(*args, **kwargs):
#             if not is_authenticated():
#                 if is_public_access_enabled():
#                     # Show warning but allow access
#                     click.echo("⚠️  Running in public access mode. Sign in for full functionality.", err=True)
#                 else:
#                     # Require authentication
#                     click.echo("Please sign in first using 'miminions auth signin'", err=True)
#                     return
#             return f(*args, **kwargs)
#         return wrapper
#     return decorator
def require_auth():
    """Temporary no-op decorator while auth is being stabilized."""
    # NOTE(auth-tests): When restoring real auth enforcement here,
    # re-enable the commented assertions in:
    # - tests/cli/test_agent.py::TestAgentCLI.test_list_agents_not_authenticated
    # - tests/cli/test_agent.py::TestAgentCLI.test_add_agent_not_authenticated
    # E2E updates are intentionally handled in a separate stream.
    def decorator(f):
        return f
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
        "base_agent": "miminions.agent.Minion",
        "mode": "cli_extension",
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

    runtime_agent = _build_cli_extension_agent(agent)
    
    # Update status
    agents[agent_id]["status"] = "running"
    save_agents(agents)
    
    if async_run:
        click.echo(f"Agent '{agent_id}' started asynchronously")
        click.echo("TODO: Async CLI execution path should stream model output and session events.")
    else:
        click.echo(f"Running agent '{agent_id}' with goal: {agent['goal']}")
        state = runtime_agent.get_state()
        click.echo(
            "Initialized core Minion runtime "
            f"(tools={state.tool_count}, has_memory={state.has_memory}, servers={len(state.connected_servers)})"
        )

        output = _execute_prompt_with_tool_fallback(runtime_agent, agent["goal"])
        click.echo(f"Agent response: {output}")
        click.echo("Agent execution completed")


@agent_cli.command("ask")
@click.argument("agent_id")
@click.option("--prompt", required=True, help="Prompt to send to the agent.")
@require_auth()
def ask_agent(agent_id, prompt):
    """Ask an agent for a one-off response without mutating its stored goal."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    runtime_agent = _build_cli_extension_agent(agent_data)
    click.echo(f"Asking agent '{agent_id}': {prompt}")
    output = _execute_prompt_with_tool_fallback(runtime_agent, prompt)
    click.echo(f"Agent response: {output}")


@agent_cli.command("tool-list")
@click.argument("agent_id")
@require_auth()
def list_agent_tools(agent_id):
    """List available tools for an agent runtime."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    runtime_agent = _build_cli_extension_agent(agent_data)
    tools = runtime_agent.list_tools()
    if not tools:
        click.echo(f"No tools available for agent '{agent_id}'.")
        return

    click.echo(f"Tools for '{agent_id}':")
    for name in tools:
        info = runtime_agent.get_tool_info(name)
        description = (info or {}).get("description", "No description")
        click.echo(f"  {name}: {description}")


@agent_cli.command("tool-info")
@click.argument("agent_id")
@click.argument("tool_name")
@require_auth()
def show_agent_tool_info(agent_id, tool_name):
    """Show detailed tool information for one tool."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    runtime_agent = _build_cli_extension_agent(agent_data)
    info = runtime_agent.get_tool_info(tool_name)
    if not info:
        click.echo(f"Tool '{tool_name}' not found for agent '{agent_id}'.", err=True)
        return

    click.echo(f"Tool: {info['name']}")
    click.echo(f"Description: {info['description']}")
    click.echo("Schema:")
    click.echo(json.dumps(info["parameters"], indent=2))


@agent_cli.command("tool-search")
@click.argument("agent_id")
@click.argument("query")
@require_auth()
def search_agent_tools(agent_id, query):
    """Search tools by name or description."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    runtime_agent = _build_cli_extension_agent(agent_data)
    matches = runtime_agent.search_tools(query)
    if not matches:
        click.echo(f"No tools matched '{query}' for agent '{agent_id}'.")
        return

    click.echo(f"Tool matches for '{query}':")
    for name in matches:
        click.echo(f"  {name}")


@agent_cli.command("tool-run")
@click.argument("agent_id")
@click.argument("tool_name")
@click.option(
    "--arguments",
    default="{}",
    help="JSON object with tool arguments, e.g. '{\"a\":2,\"b\":3}'.",
)
@require_auth()
def run_agent_tool(agent_id, tool_name, arguments):
    """Run one tool and print structured execution output."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    try:
        parsed_arguments = json.loads(arguments)
    except json.JSONDecodeError:
        click.echo("Invalid JSON for --arguments.", err=True)
        return

    if not isinstance(parsed_arguments, dict):
        click.echo("--arguments must be a JSON object.", err=True)
        return

    runtime_agent = _build_cli_extension_agent(agent_data)
    result = runtime_agent.execute(tool_name, arguments=parsed_arguments)

    click.echo(f"Tool: {result.tool_name}")
    click.echo(f"Status: {result.status.value}")
    if result.error:
        click.echo(f"Error: {result.error}")
    else:
        click.echo(f"Result: {result.result}")
    click.echo(f"Execution time (ms): {result.execution_time_ms:.2f}")


# TODO(cli-agent): Add commands for memory backends and memory tools:
# - memory-attach --backend {sqlite,md}
# - memory-store / memory-recall / memory-update / memory-delete
# - ingest-document
#
# TODO(cli-agent): Add MCP server integration commands:
# - mcp-connect
# - mcp-load-tools
# - mcp-disconnect