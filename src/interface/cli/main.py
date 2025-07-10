"""
MiMinions CLI - Main command line interface for the MiMinions package.
"""

import click
from .auth import auth_cli
from .agent import agent_cli
from .task import task_cli
from .workflow import workflow_cli
from .knowledge import knowledge_cli


@click.group()
@click.version_option()
def cli():
    """MiMinions CLI - Manage AI agents, tasks, workflows and knowledge."""
    pass


# Register command groups
cli.add_command(auth_cli, name="auth")
cli.add_command(agent_cli, name="agent")
cli.add_command(task_cli, name="task")
cli.add_command(workflow_cli, name="workflow")
cli.add_command(knowledge_cli, name="knowledge")


if __name__ == "__main__":
    cli()