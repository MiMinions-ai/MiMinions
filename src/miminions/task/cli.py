"""
Task management CLI commands.

Refactored from interface/cli/task.py to use Task models and repository.
"""

import click
import uuid
from datetime import datetime
from pathlib import Path

from .models import Task, TaskStatus, TaskPriority
from .repository import TaskRepository
from .exceptions import TaskNotFoundError


def get_task_db_path() -> Path:
    """Get the task database file path."""
    # Use same config directory as auth
    from ..interface.cli.auth import get_config_dir
    config_dir = get_config_dir()
    return config_dir / "tasks.db"


def get_repository() -> TaskRepository:
    """Get task repository instance."""
    db_path = get_task_db_path()
    return TaskRepository(db_path)


def require_auth():
    """Decorator to require authentication or allow public access."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            from ..interface.cli.auth import is_authenticated, is_public_access_enabled
            if not is_authenticated():
                if is_public_access_enabled():
                    click.echo("⚠️  Running in public access mode. Sign in for full functionality.", err=True)
                else:
                    click.echo("Please sign in first using 'miminions auth signin'", err=True)
                    return
            return f(*args, **kwargs)
        return wrapper
    return decorator


@click.group()
def task_cli():
    """Task management commands."""
    pass


@task_cli.command("list")
@click.option("--status", type=click.Choice(["pending", "running", "completed", "failed", "cancelled"]), help="Filter by status")
@require_auth()
def list_tasks(status):
    """List all tasks."""
    with get_repository() as repo:
        task_status = TaskStatus(status) if status else None
        tasks = repo.load_all_tasks(status=task_status)

    if not tasks:
        click.echo("No tasks found.")
        return

    click.echo("Tasks:")
    for task in tasks:
        priority_label = "high" if task.priority <= 20 else "medium" if task.priority <= 70 else "low"
        click.echo(
            f"  {task.task_id[:8]}: {task.name} "
            f"({task.status.value}, priority={priority_label}) "
            f"- {task.input_data.get('description', 'No description')}"
        )


@task_cli.command("add")
@click.option("--title", prompt="Task title", help="Title of the task")
@click.option("--description", prompt="Description", help="Description of the task")
@click.option("--priority", type=click.Choice(["low", "medium", "high"]), default="medium", help="Priority level")
@click.option("--agent", help="Agent ID to assign the task to")
@require_auth()
def add_task(title, description, priority, agent):
    """Add a new task."""
    # Map priority labels to values
    priority_map = {
        "high": TaskPriority.HIGH,
        "medium": TaskPriority.MEDIUM,
        "low": TaskPriority.LOW
    }

    task = Task(
        task_id=str(uuid.uuid4()),
        name=title,
        priority=priority_map[priority],
        status=TaskStatus.PENDING,
        assigned_agent_id=agent,
        input_data={"description": description},
        created_at=datetime.now()
    )

    with get_repository() as repo:
        repo.save_task(task)

    click.echo(f"Task '{title}' added successfully with ID: {task.task_id[:8]}")


@task_cli.command("update")
@click.argument("task_id")
@click.option("--title", help="New title for the task")
@click.option("--description", help="New description for the task")
@click.option("--priority", type=click.Choice(["low", "medium", "high"]), help="New priority level")
@click.option("--status", type=click.Choice(["pending", "running", "completed", "failed", "cancelled"]), help="New status")
@click.option("--agent", help="Agent ID to assign the task to")
@require_auth()
def update_task(task_id, title, description, priority, status, agent):
    """Update an existing task."""
    with get_repository() as repo:
        try:
            # Find task by partial ID match
            all_tasks = repo.load_all_tasks()
            matching_tasks = [t for t in all_tasks if t.task_id.startswith(task_id)]

            if not matching_tasks:
                click.echo(f"Task '{task_id}' not found.", err=True)
                return

            if len(matching_tasks) > 1:
                click.echo(f"Ambiguous task ID '{task_id}'. Multiple matches found.", err=True)
                return

            task = matching_tasks[0]

            # Update fields
            if title:
                task.name = title
            if description:
                task.input_data["description"] = description
            if priority:
                priority_map = {
                    "high": TaskPriority.HIGH,
                    "medium": TaskPriority.MEDIUM,
                    "low": TaskPriority.LOW
                }
                task.priority = priority_map[priority]
            if status:
                task.status = TaskStatus(status)
            if agent:
                task.assigned_agent_id = agent

            repo.save_task(task)
            click.echo(f"Task '{task.task_id[:8]}' updated successfully")

        except TaskNotFoundError:
            click.echo(f"Task '{task_id}' not found.", err=True)


@task_cli.command("remove")
@click.argument("task_id")
@click.confirmation_option(prompt="Are you sure you want to remove this task?")
@require_auth()
def remove_task(task_id):
    """Remove a task."""
    with get_repository() as repo:
        try:
            # Find task by partial ID match
            all_tasks = repo.load_all_tasks()
            matching_tasks = [t for t in all_tasks if t.task_id.startswith(task_id)]

            if not matching_tasks:
                click.echo(f"Task '{task_id}' not found.", err=True)
                return

            if len(matching_tasks) > 1:
                click.echo(f"Ambiguous task ID '{task_id}'. Multiple matches found.", err=True)
                return

            task = matching_tasks[0]
            repo.delete_task(task.task_id)
            click.echo(f"Task '{task.task_id[:8]}' removed successfully")

        except TaskNotFoundError:
            click.echo(f"Task '{task_id}' not found.", err=True)


@task_cli.command("show")
@click.argument("task_id")
@require_auth()
def show_task(task_id):
    """Show detailed information about a task."""
    with get_repository() as repo:
        try:
            # Find task by partial ID match
            all_tasks = repo.load_all_tasks()
            matching_tasks = [t for t in all_tasks if t.task_id.startswith(task_id)]

            if not matching_tasks:
                click.echo(f"Task '{task_id}' not found.", err=True)
                return

            if len(matching_tasks) > 1:
                click.echo(f"Ambiguous task ID '{task_id}'. Multiple matches found.", err=True)
                return

            task = matching_tasks[0]

            priority_label = "high" if task.priority <= 20 else "medium" if task.priority <= 70 else "low"

            click.echo(f"Task ID: {task.task_id}")
            click.echo(f"Title: {task.name}")
            click.echo(f"Description: {task.input_data.get('description', 'No description')}")
            click.echo(f"Priority: {priority_label} ({task.priority})")
            click.echo(f"Status: {task.status.value}")
            click.echo(f"Agent: {task.assigned_agent_id or 'Not assigned'}")
            click.echo(f"Created: {task.created_at.isoformat()}")

            if task.started_at:
                click.echo(f"Started: {task.started_at.isoformat()}")
            if task.completed_at:
                click.echo(f"Completed: {task.completed_at.isoformat()}")
            if task.error_message:
                click.echo(f"Error: {task.error_message}")

            # Show dependencies if any
            dependencies = repo.load_dependencies(task.task_id)
            if dependencies:
                click.echo(f"Dependencies: {', '.join(d[:8] for d in dependencies)}")

            dependents = repo.load_dependents(task.task_id)
            if dependents:
                click.echo(f"Dependents: {', '.join(d[:8] for d in dependents)}")

        except TaskNotFoundError:
            click.echo(f"Task '{task_id}' not found.", err=True)


@task_cli.command("duplicate")
@click.argument("task_id")
@click.option("--title", help="Title for the duplicated task")
@require_auth()
def duplicate_task(task_id, title):
    """Duplicate an existing task."""
    with get_repository() as repo:
        try:
            # Find task by partial ID match
            all_tasks = repo.load_all_tasks()
            matching_tasks = [t for t in all_tasks if t.task_id.startswith(task_id)]

            if not matching_tasks:
                click.echo(f"Task '{task_id}' not found.", err=True)
                return

            if len(matching_tasks) > 1:
                click.echo(f"Ambiguous task ID '{task_id}'. Multiple matches found.", err=True)
                return

            original_task = matching_tasks[0]

            # Create new task
            new_task = Task(
                task_id=str(uuid.uuid4()),
                name=title or f"{original_task.name} (copy)",
                priority=original_task.priority,
                status=TaskStatus.PENDING,
                assigned_agent_id=None,  # Don't copy agent assignment
                input_data=original_task.input_data.copy(),
                created_at=datetime.now(),
                timeout_seconds=original_task.timeout_seconds,
                max_retries=original_task.max_retries
            )

            repo.save_task(new_task)
            click.echo(f"Task duplicated successfully with ID: {new_task.task_id[:8]}")

        except TaskNotFoundError:
            click.echo(f"Task '{task_id}' not found.", err=True)
