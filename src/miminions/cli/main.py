"""
MiMinions CLI - Main command line interface for the MiMinions package.
"""

import click
from miminions import __version__
from miminions.core.bootstrap import ensure_default_setup
from .auth import auth_cli, get_config_dir
from .agent import agent_cli
from .task import task_cli
from .knowledge import knowledge_cli
from .workspace import workspace_cli
from .execution import execution_cli
from .chat import chat_cli
from .gateway import gateway_cli
from .prompt import prompt_cli
from .config import config_cli


@click.group()
@click.version_option(version=__version__, prog_name="miminions")
def cli():
    """MiMinions CLI - Manage AI agents, tasks, workflows and knowledge."""
    try:
        ensure_default_setup(get_config_dir())
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc


@click.command("init")
@click.option(
    "--force",
    is_flag=True,
    help="Re-run bootstrap and restore any missing default template files.",
)
def init_cli(force: bool):
    """Initialize or repair the default CLI bootstrap state."""
    try:
        config = ensure_default_setup(get_config_dir(), force=force)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc

    click.echo(f"Default workspace: {config.get('default_workspace')}")
    click.echo(f"Default agent: {config.get('default_agent')}")
    if force:
        click.echo("Bootstrap repair complete.")
    else:
        click.echo("Bootstrap initialization complete.")


# Register command groups
cli.add_command(auth_cli, name="auth")
cli.add_command(agent_cli, name="agent")
cli.add_command(task_cli, name="task")
# cli.add_command(workflow_cli, name="workflow") #TODO: workflow management is not yet implemented
cli.add_command(knowledge_cli, name="knowledge")
cli.add_command(workspace_cli, name="workspace")
cli.add_command(execution_cli, name="execution")
cli.add_command(chat_cli, name="chat")
cli.add_command(gateway_cli, name="gateway")
cli.add_command(prompt_cli, name="prompt")
cli.add_command(config_cli, name="config")
cli.add_command(init_cli, name="init")

def main():
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
