"""
MiMinions CLI - Main command line interface for the MiMinions package.
"""

import click
from .auth import auth_cli
from .agent import agent_cli
from .task import task_cli
from .workflow import workflow_cli
from .knowledge import knowledge_cli
from .workspace import workspace_cli
from .chat import chat_cli


@click.group()
@click.version_option()
def cli():
    """MiMinions CLI - Manage AI agents, tasks, workflows and knowledge."""
    pass


# Register command groups
cli.add_command(auth_cli, name="auth")
cli.add_command(agent_cli, name="agent")
cli.add_command(task_cli, name="task")
# cli.add_command(workflow_cli, name="workflow") #TODO: workflow management is not yet implemented
cli.add_command(knowledge_cli, name="knowledge")
cli.add_command(workspace_cli, name="workspace")
cli.add_command(chat_cli, name="chat")


if __name__ == "__main__":
    cli()