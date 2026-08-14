"""
Agent management commands for MiMinions CLI.
"""

import click
import asyncio
import json
import re
from datetime import datetime, timezone
from enum import Enum
from .auth import get_config_dir
from .persistence import load_json, save_json
from miminions.core.auth import require_auth
from miminions.agent import create_minion
from mcp import StdioServerParameters


class AgentAction(str, Enum):
    """Supported operations for a prepared CLI agent runtime."""

    RUN = "run"
    ASK = "ask"
    TOOL_LIST = "tool-list"
    TOOL_INFO = "tool-info"
    TOOL_SEARCH = "tool-search"
    TOOL_RUN = "tool-run"


_ACTION_PARAM_TYPES = {
    AgentAction.RUN: {"prompt": str},
    AgentAction.ASK: {"prompt": str},
    AgentAction.TOOL_LIST: {},
    AgentAction.TOOL_INFO: {"tool_name": str},
    AgentAction.TOOL_SEARCH: {"query": str},
    AgentAction.TOOL_RUN: {"tool_name": str, "arguments": dict},
}


def _slugify(name):
    """Turn a friendly name into a filesystem/id-safe slug.

    Collapses any run of non-alphanumeric characters into a single underscore
    so distinct-looking names don't silently diverge; falls back to "agent"
    when a name has no usable characters.
    """
    slug = re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")
    return slug or "agent"


def _unique_agent_id(name, agents):
    """Derive a unique agent id from a name, suffixing on collision."""
    base = _slugify(name)
    agent_id = base
    suffix = 2
    while agent_id in agents:
        agent_id = f"{base}_{suffix}"
        suffix += 1
    return agent_id


def get_agents_file():
    """Get the agents configuration file path."""
    return get_config_dir() / "agents.json"


def load_agents():
    """Load agents from configuration."""
    return load_json(get_agents_file())


def save_agents(agents):
    """Save agents to configuration."""
    save_json(get_agents_file(), agents)


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


def _validate_agent_action(operation, params):
    """Return a validated action or raise a user-facing Click error."""
    try:
        action = AgentAction(operation)
    except (TypeError, ValueError) as exc:
        raise click.ClickException(
            f"Unsupported agent runtime operation: {operation}"
        ) from exc

    expected = _ACTION_PARAM_TYPES[action]
    missing = expected.keys() - params.keys()
    if missing:
        names = ", ".join(sorted(missing))
        raise click.ClickException(
            f"Missing parameter(s) for agent action '{action.value}': {names}"
        )

    unexpected = params.keys() - expected.keys()
    if unexpected:
        names = ", ".join(sorted(unexpected))
        raise click.ClickException(
            f"Unexpected parameter(s) for agent action '{action.value}': {names}"
        )

    for name, expected_type in expected.items():
        value = params[name]
        if not isinstance(value, expected_type):
            raise click.ClickException(
                f"Invalid parameter '{name}' for agent action '{action.value}': "
                f"expected {expected_type.__name__}"
            )
        if expected_type is str and not value.strip():
            raise click.ClickException(
                f"Invalid parameter '{name}' for agent action '{action.value}': "
                "value cannot be empty"
            )
    return action


async def _execute_agent_action(runtime_agent, operation, **params):
    """Execute one supported CLI operation against a prepared agent runtime."""
    action = _validate_agent_action(operation, params)
    if action is AgentAction.RUN:
        state = runtime_agent.get_state()
        click.echo(
            "Initialized core Minion runtime "
            f"(tools={state.tool_count}, has_memory={state.has_memory}, "
            f"servers={len(state.connected_servers)})"
        )
        return await _execute_prompt_with_tool_fallback(runtime_agent, params["prompt"])
    if action is AgentAction.ASK:
        return await _execute_prompt_with_tool_fallback(runtime_agent, params["prompt"])
    if action is AgentAction.TOOL_LIST:
        return [
            (name, runtime_agent.get_tool_info(name))
            for name in runtime_agent.list_tools()
        ]
    if action is AgentAction.TOOL_INFO:
        return runtime_agent.get_tool_info(params["tool_name"])
    if action is AgentAction.TOOL_SEARCH:
        return runtime_agent.search_tools(params["query"])
    if action is AgentAction.TOOL_RUN:
        return await runtime_agent.execute_async(
            params["tool_name"], arguments=params["arguments"]
        )


async def _run_with_agent_runtime(agent_data, operation, **params):
    """Build an agent, attach its configured MCP servers, and always clean up."""
    runtime_agent = _build_cli_extension_agent(agent_data)
    try:
        for server_name, config in agent_data.get("mcp_servers", {}).items():
            try:
                server_params = StdioServerParameters(
                    command=config["command"],
                    args=list(config.get("args", [])),
                )
                await runtime_agent.connect_mcp_server(server_name, server_params)
                await runtime_agent.load_tools_from_mcp_server(server_name)
            except Exception as exc:
                raise click.ClickException(
                    f"Failed to load MCP server '{server_name}': {exc}"
                ) from exc
        return await _execute_agent_action(runtime_agent, operation, **params)
    finally:
        await runtime_agent.cleanup(rebuild=False)


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


def _resolve_agent_id(agent_id: str | None) -> str | None:
    """Return agent_id, falling back to default_agent from config when None."""
    if agent_id:
        return agent_id
    default = get_config().get("default_agent")
    if not default:
        raise click.ClickException(
            "No agent id given and no default_agent configured. "
            "Pass an agent id or run 'miminions agent add' first."
        )
    return default


def _get_agent_record_or_error(agent_id: str | None):
    """Resolve and load one persisted CLI agent record with user-facing errors."""
    agent_id = _resolve_agent_id(agent_id)
    agents = load_agents()
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return None
    return agents[agent_id]


def _resolve_agent_ref_or_error(agent_ref: str, agents: dict) -> str | None:
    """Resolve an agent by exact id, id prefix, or exact name."""
    if agent_ref in agents:
        return agent_ref

    matches = []

    for current_id in agents:
        if str(current_id).startswith(agent_ref):
            matches.append(current_id)

    for current_id, data in agents.items():
        if str(data.get("name", "")) == agent_ref and current_id not in matches:
            matches.append(current_id)

    if not matches:
        click.echo(f"Agent '{agent_ref}' not found.", err=True)
        return None

    if len(matches) > 1:
        click.echo(
            f"Agent reference '{agent_ref}' is ambiguous: {', '.join(matches)}",
            err=True,
        )
        return None

    return matches[0]


def _extract_first_two_ints(text):
    """Extract first two integers from text for simple arithmetic routing."""
    values = [int(v) for v in re.findall(r"-?\d+", text)]
    if len(values) >= 2:
        return values[0], values[1]
    return None


async def _execute_prompt_with_tool_fallback(runtime_agent, prompt):
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

    output = await runtime_agent.run(prompt)

    return output


@click.group()
def agent_cli():
    """Agent management commands."""
    pass


@agent_cli.command("list")
<<<<<<< HEAD
@require_auth
def list_agents():
=======
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
@require_auth()
def list_agents(as_json):
>>>>>>> upstream/development
    """List all agents."""
    agents = load_agents()

    if as_json:
        payload = [
            {
                "id": agent_id,
                "name": agent_data.get("name", agent_id),
                "description": agent_data.get("description", "No description"),
                "status": agent_data.get("status", "inactive"),
                "type": agent_data.get("type"),
                "goal": agent_data.get("goal"),
            }
            for agent_id, agent_data in agents.items()
        ]
        click.echo(json.dumps(payload, indent=2))
        return
    
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
@require_auth
def add_agent(name, description, type):
    """Add a new agent."""
    agents = load_agents()

    agent_id = _unique_agent_id(name, agents)

    agents[agent_id] = {
        "name": name,
        "description": description,
        "type": type,
        "base_agent": "miminions.agent.Minion",
        "mode": "cli_extension",
        "status": "inactive",
        "goal": None,
        "created_at": datetime.now(timezone.utc).isoformat()
    }
    
    save_agents(agents)
    click.echo(f"Agent '{name}' added successfully with ID: {agent_id}")


@agent_cli.command("update")
@click.argument("agent_id")
@click.option("--name", help="New name for the agent")
@click.option("--description", help="New description for the agent")
@click.option("--type", help="New type for the agent")
@require_auth
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


@agent_cli.command("show")
@click.argument("agent_ref")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
@require_auth()
def show_agent(agent_ref, as_json):
    """Show one agent by id, id prefix, or exact name."""
    agents = load_agents()
    if not agents:
        click.echo("No agents configured.")
        return

    agent_id = _resolve_agent_ref_or_error(agent_ref, agents)
    if not agent_id:
        return

    agent = agents[agent_id]
    payload = {
        "id": agent_id,
        "name": agent.get("name", agent_id),
        "description": agent.get("description", "No description"),
        "type": agent.get("type", "unknown"),
        "status": agent.get("status", "inactive"),
        "goal": agent.get("goal"),
        "base_agent": agent.get("base_agent", "miminions.agent.Minion"),
        "mode": agent.get("mode", "cli_extension"),
        "created_at": agent.get("created_at", ""),
    }

    if as_json:
        click.echo(json.dumps(payload, indent=2))
        return

    click.echo(f"Agent: {agent.get('name', agent_id)}")
    click.echo(f"ID: {agent_id}")
    click.echo(f"Description: {agent.get('description', 'No description')}")
    click.echo(f"Type: {agent.get('type', 'unknown')}")
    click.echo(f"Status: {agent.get('status', 'inactive')}")
    click.echo(f"Goal: {agent.get('goal')}")
    click.echo(f"Base Agent: {agent.get('base_agent', 'miminions.agent.Minion')}")
    click.echo(f"Mode: {agent.get('mode', 'cli_extension')}")
    click.echo(f"Created: {agent.get('created_at', '')}")


@agent_cli.command("remove")
@click.argument("agent_id")
@click.confirmation_option(prompt="Are you sure you want to remove this agent?")
@require_auth
def remove_agent(agent_id):
    """Remove an agent."""
    agents = load_agents()
    
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return
    
    del agents[agent_id]
    save_agents(agents)
    click.echo(f"Agent '{agent_id}' removed successfully")


@agent_cli.command("mcp-add")
@click.argument("agent_id")
@click.argument("server_name")
@click.option("--command", required=True, help="MCP server executable.")
@click.option("--arg", "args", multiple=True, help="MCP server argument; may be repeated.")
@require_auth
def add_mcp_server(agent_id, server_name, command, args):
    """Register a stdio MCP server for an agent without starting it."""
    agents = load_agents()
    if agent_id not in agents:
        raise click.ClickException(f"Agent '{agent_id}' not found.")
    command = command.strip()
    if not command:
        raise click.ClickException("MCP server command cannot be empty.")
    servers = agents[agent_id].setdefault("mcp_servers", {})
    if server_name in servers:
        raise click.ClickException(
            f"MCP server '{server_name}' already exists for agent '{agent_id}'."
        )
    servers[server_name] = {"command": command, "args": list(args)}
    save_agents(agents)
    click.echo(f"MCP server '{server_name}' added to agent '{agent_id}'.")


@agent_cli.command("mcp-list")
@click.argument("agent_id")
@require_auth
def list_mcp_servers(agent_id):
    """List MCP servers registered for an agent."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return
    servers = agent_data.get("mcp_servers", {})
    if not servers:
        click.echo(f"No MCP servers configured for agent '{agent_id}'.")
        return
    click.echo(f"MCP servers for '{agent_id}':")
    for name, config in servers.items():
        command = " ".join([config["command"], *config.get("args", [])])
        click.echo(f"  {name}: {command}")


@agent_cli.command("mcp-remove")
@click.argument("agent_id")
@click.argument("server_name")
@click.confirmation_option(prompt="Are you sure you want to remove this MCP server?")
@require_auth
def remove_mcp_server(agent_id, server_name):
    """Remove an MCP server registration from an agent."""
    agents = load_agents()
    if agent_id not in agents:
        raise click.ClickException(f"Agent '{agent_id}' not found.")
    servers = agents[agent_id].get("mcp_servers", {})
    if server_name not in servers:
        raise click.ClickException(
            f"MCP server '{server_name}' not found for agent '{agent_id}'."
        )
    del servers[server_name]
    save_agents(agents)
    click.echo(f"MCP server '{server_name}' removed from agent '{agent_id}'.")


@agent_cli.command("set-goal")
@click.argument("agent_id", required=False, default=None)
@click.option("--goal", prompt="Goal", help="Goal for the agent")
@require_auth
def set_goal(agent_id, goal):
    """Set a goal for an agent (defaults to the configured default agent)."""
    agent_id = _resolve_agent_id(agent_id)
    agents = load_agents()

    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return

    agents[agent_id]["goal"] = goal
    save_agents(agents)
    click.echo(f"Goal set for agent '{agent_id}': {goal}")


@agent_cli.command("run")
@click.argument("agent_id", required=False, default=None)
@click.option("--async", "async_run", is_flag=True, help="Run agent asynchronously")
@require_auth
def run_agent(agent_id, async_run):
    """Run an agent (defaults to the configured default agent)."""
    agent_id = _resolve_agent_id(agent_id)
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
        click.echo("TODO: Async CLI execution path should stream model output and session events.")
    else:
        click.echo(f"Running agent '{agent_id}' with goal: {agent['goal']}")
        output = asyncio.run(
            _run_with_agent_runtime(agent, AgentAction.RUN, prompt=agent["goal"])
        )
        click.echo(f"Agent response: {output}")
        click.echo("Agent execution completed")


@agent_cli.command("ask")
@click.argument("agent_id", required=False, default=None)
@click.option("--prompt", required=True, help="Prompt to send to the agent.")
@require_auth
def ask_agent(agent_id, prompt):
    """Ask an agent for a one-off response (defaults to the configured default agent)."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    click.echo(f"Asking agent '{agent_id}': {prompt}")
    output = asyncio.run(
        _run_with_agent_runtime(agent_data, AgentAction.ASK, prompt=prompt)
    )
    click.echo(f"Agent response: {output}")


@agent_cli.command("tool-list")
<<<<<<< HEAD
@click.argument("agent_id")
@require_auth
=======
@click.argument("agent_id", required=False, default=None)
@require_auth()
>>>>>>> upstream/development
def list_agent_tools(agent_id):
    """List available tools for an agent runtime (defaults to the configured default agent)."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    tools = asyncio.run(_run_with_agent_runtime(agent_data, AgentAction.TOOL_LIST))
    if not tools:
        click.echo(f"No tools available for agent '{agent_id}'.")
        return

    click.echo(f"Tools for '{agent_id}':")
    for name, info in tools:
        description = (info or {}).get("description", "No description")
        click.echo(f"  {name}: {description}")


@agent_cli.command("tool-info")
@click.argument("agent_id", required=False, default=None)
@click.argument("tool_name")
@require_auth
def show_agent_tool_info(agent_id, tool_name):
    """Show detailed tool information for one tool (defaults to the configured default agent)."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    info = asyncio.run(
        _run_with_agent_runtime(
            agent_data, AgentAction.TOOL_INFO, tool_name=tool_name
        )
    )
    if not info:
        click.echo(f"Tool '{tool_name}' not found for agent '{agent_id}'.", err=True)
        return

    click.echo(f"Tool: {info['name']}")
    click.echo(f"Description: {info['description']}")
    click.echo("Schema:")
    click.echo(json.dumps(info["parameters"], indent=2))


@agent_cli.command("tool-search")
@click.argument("agent_id", required=False, default=None)
@click.argument("query")
@require_auth
def search_agent_tools(agent_id, query):
    """Search tools by name or description (defaults to the configured default agent)."""
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        return

    matches = asyncio.run(
        _run_with_agent_runtime(agent_data, AgentAction.TOOL_SEARCH, query=query)
    )
    if not matches:
        click.echo(f"No tools matched '{query}' for agent '{agent_id}'.")
        return

    click.echo(f"Tool matches for '{query}':")
    for name in matches:
        click.echo(f"  {name}")


@agent_cli.command("tool-run")
@click.argument("agent_id", required=False, default=None)
@click.argument("tool_name")
@click.option(
    "--arguments",
    default="{}",
    help="JSON object with tool arguments, e.g. '{\"a\":2,\"b\":3}'.",
)
@require_auth
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

    result = asyncio.run(
        _run_with_agent_runtime(
            agent_data,
            AgentAction.TOOL_RUN,
            tool_name=tool_name,
            arguments=parsed_arguments,
        )
    )

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
