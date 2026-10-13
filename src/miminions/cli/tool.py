"""Tool discovery and execution commands for the MiMinions CLI."""

import asyncio
import json

import click


from .agent import AgentAction, _get_agent_record_or_error, _run_with_agent_runtime
from .dispatch import attachment_options, submit_task, validate_attachment


def _split_optional_agent_operand(agent_id, operand, operand_name):
    """Support either ``[agent-id] <operand>`` or ``<operand>`` with a default agent."""
    if operand is not None:
        return agent_id, operand
    if agent_id is None:
        raise click.UsageError(f"Missing argument '{operand_name.upper()}'.")
    return None, agent_id


@click.group("tool")
def tool_cli():
    """Discover, inspect, and execute tools and tool sessions."""


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


@tool_cli.command("execute")
@click.argument("agent_id", required=False, default=None)
@click.argument("tool_name", required=False, default=None)
@click.option(
    "--arguments",
    default="{}",
    help="JSON object with tool arguments, e.g. '{\"a\":2,\"b\":3}'.",
)
@attachment_options
def execute_agent_tool(agent_id, tool_name, arguments, attach=False, detach=False):
    """Execute one saved-agent tool and print structured output."""
    validate_attachment(attach, detach)
    agent_id, tool_name = _split_optional_agent_operand(
        agent_id, tool_name, "tool_name"
    )
    agent_data = _get_agent_record_or_error(agent_id)
    if not agent_data:
        raise click.exceptions.Exit(1)

    try:
        parsed_arguments = json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise click.ClickException("Invalid JSON for --arguments.") from exc

    if not isinstance(parsed_arguments, dict):
        raise click.ClickException("--arguments must be a JSON object.")

    from miminions.core.paths import get_config_dir
    submit_task("agent_tool", {"agent": agent_data, "tool_name": tool_name, "arguments": parsed_arguments},
                attach=attach, detach=detach, home=get_config_dir())


# Execution sessions share the public ``tool`` namespace while retaining their
# independent persistence and tracing implementation.
from .execution import add_tool, history, run_test, session

tool_cli.add_command(session)
tool_cli.add_command(add_tool)
tool_cli.add_command(history)
tool_cli.add_command(run_test)
