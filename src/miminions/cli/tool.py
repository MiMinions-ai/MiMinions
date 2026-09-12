"""Tool discovery and execution commands for the MiMinions CLI."""

import asyncio
import json

import click

from miminions.tools.schemas import ToolExecutionResult

from .agent import AgentAction, _get_agent_record_or_error, _run_with_agent_runtime


def _split_optional_agent_operand(agent_id, operand, operand_name):
    """Support either ``[agent-id] <operand>`` or ``<operand>`` with a default agent."""
    if operand is not None:
        return agent_id, operand
    if agent_id is None:
        raise click.UsageError(f"Missing argument '{operand_name.upper()}'.")
    return None, agent_id


@click.group("tool")
def tool_cli():
    """Discover, inspect, and run tools for an agent."""


@tool_cli.command("list")
@click.argument("agent_id", required=False, default=None)
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
        if not isinstance(info, dict):
            click.echo(f"Unexpected tool info format for '{name}': {info}", err=True)
            continue
        description = (info or {}).get("description", "No description")
        click.echo(f"  {name}: {description}")


@tool_cli.command("info")
@click.argument("agent_id", required=False, default=None)
@click.argument("tool_name", required=False, default=None)
def show_agent_tool_info(agent_id, tool_name):
    """Show detailed tool information for one tool (defaults to the configured default agent)."""
    agent_id, tool_name = _split_optional_agent_operand(
        agent_id, tool_name, "tool_name"
    )
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

    if not isinstance(info, dict):
        click.echo(f"Unexpected tool info format for '{tool_name}': {info}", err=True)
        return

    click.echo(f"Tool: {info['name']}")
    click.echo(f"Description: {info['description']}")
    click.echo("Schema:")
    click.echo(json.dumps(info["parameters"], indent=2))


@tool_cli.command("search")
@click.argument("agent_id", required=False, default=None)
@click.argument("query", required=False, default=None)
def search_agent_tools(agent_id, query):
    """Search tools by name or description (defaults to the configured default agent)."""
    agent_id, query = _split_optional_agent_operand(agent_id, query, "query")
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


@tool_cli.command("run")
@click.argument("agent_id", required=False, default=None)
@click.argument("tool_name", required=False, default=None)
@click.option(
    "--arguments",
    default="{}",
    help="JSON object with tool arguments, e.g. '{\"a\":2,\"b\":3}'.",
)
def run_agent_tool(agent_id, tool_name, arguments):
    """Run one tool and print structured execution output."""
    agent_id, tool_name = _split_optional_agent_operand(
        agent_id, tool_name, "tool_name"
    )
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

    if isinstance(result, str):
        click.echo(f"Tool execution returned: {result}", err=False)
        return

    if not isinstance(result, ToolExecutionResult):
        click.echo(f"Unexpected tool execution result format: {type(result)}", err=True)
        return

    click.echo(f"Tool: {result.tool_name}")
    click.echo(f"Status: {result.status.value}")
    if result.error:
        click.echo(f"Error: {result.error}")
    else:
        click.echo(f"Result: {result.result}")
    click.echo(f"Execution time (ms): {result.execution_time_ms:.2f}")
