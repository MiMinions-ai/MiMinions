"""
Task management commands for MiMinions CLI.
"""

import click
import json
import uuid
from pathlib import Path
from .auth import get_config_dir, is_authenticated, is_public_access_enabled


def get_tasks_file():
    """Get the tasks configuration file path."""
    return get_config_dir() / "tasks.json"


def load_tasks():
    """Load tasks from configuration."""
    tasks_file = get_tasks_file()
    if not tasks_file.exists():
        return {}
    
    with open(tasks_file, "r") as f:
        return json.load(f)


def save_tasks(tasks):
    """Save tasks to configuration."""
    tasks_file = get_tasks_file()
    with open(tasks_file, "w") as f:
        json.dump(tasks, f, indent=2)


def require_auth():
    """Decorator to require authentication or allow public access."""
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                if is_public_access_enabled():
                    # Show warning but allow access
                    click.echo("⚠️  Running in public access mode. Sign in for full functionality.", err=True)
                else:
                    # Require authentication
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
@require_auth()
def list_tasks():
    """List all tasks."""
    tasks = load_tasks()
    
    if not tasks:
        click.echo("No tasks configured.")
        return
    
    click.echo("Tasks:")
    for task_id, task_data in tasks.items():
        status = task_data.get("status", "pending")
        title = task_data.get("title", task_id)
        description = task_data.get("description", "No description")
        priority = task_data.get("priority", "medium")
        click.echo(f"  {task_id}: {title} ({status}, {priority}) - {description}")


@task_cli.command("add")
@click.option("--title", prompt="Task title", help="Title of the task")
@click.option("--description", prompt="Description", help="Description of the task")
@click.option("--priority", type=click.Choice(["low", "medium", "high"]), default="medium", help="Priority level")
@click.option("--agent", help="Agent ID to assign the task to")
@require_auth()
def add_task(title, description, priority, agent):
    """Add a new task."""
    tasks = load_tasks()
    
    # Generate a unique ID
    task_id = str(uuid.uuid4())[:8]
    
    tasks[task_id] = {
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pending",
        "agent": agent,
        "created_at": click.get_current_context().meta.get("timestamp", ""),
        "updated_at": None
    }
    
    save_tasks(tasks)
    click.echo(f"Task '{title}' added successfully with ID: {task_id}")


@task_cli.command("update")
@click.argument("task_id")
@click.option("--title", help="New title for the task")
@click.option("--description", help="New description for the task")
@click.option("--priority", type=click.Choice(["low", "medium", "high"]), help="New priority level")
@click.option("--status", type=click.Choice(["pending", "in_progress", "completed", "cancelled"]), help="New status")
@click.option("--agent", help="Agent ID to assign the task to")
@require_auth()
def update_task(task_id, title, description, priority, status, agent):
    """Update an existing task."""
    tasks = load_tasks()
    
    if task_id not in tasks:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return
    
    task = tasks[task_id]
    
    if title:
        task["title"] = title
    if description:
        task["description"] = description
    if priority:
        task["priority"] = priority
    if status:
        task["status"] = status
    if agent:
        task["agent"] = agent
    
    task["updated_at"] = click.get_current_context().meta.get("timestamp", "")
    
    save_tasks(tasks)
    click.echo(f"Task '{task_id}' updated successfully")


@task_cli.command("remove")
@click.argument("task_id")
@click.confirmation_option(prompt="Are you sure you want to remove this task?")
@require_auth()
def remove_task(task_id):
    """Remove a task."""
    tasks = load_tasks()
    
    if task_id not in tasks:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return
    
    del tasks[task_id]
    save_tasks(tasks)
    click.echo(f"Task '{task_id}' removed successfully")


@task_cli.command("duplicate")
@click.argument("task_id")
@click.option("--title", help="Title for the duplicated task")
@require_auth()
def duplicate_task(task_id, title):
    """Duplicate an existing task."""
    tasks = load_tasks()
    
    if task_id not in tasks:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return
    
    # Create a copy of the task
    original_task = tasks[task_id].copy()
    new_task_id = str(uuid.uuid4())[:8]
    
    # Update the title if provided
    if title:
        original_task["title"] = title
    else:
        original_task["title"] = f"{original_task['title']} (copy)"
    
    # Reset certain fields
    original_task["status"] = "pending"
    original_task["created_at"] = click.get_current_context().meta.get("timestamp", "")
    original_task["updated_at"] = None
    
    tasks[new_task_id] = original_task
    save_tasks(tasks)
    click.echo(f"Task duplicated successfully with ID: {new_task_id}")


@task_cli.command("show")
@click.argument("task_id")
@require_auth()
def show_task(task_id):
    """Show detailed information about a task."""
    tasks = load_tasks()
    
    if task_id not in tasks:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return
    
    task = tasks[task_id]
    
    click.echo(f"Task ID: {task_id}")
    click.echo(f"Title: {task['title']}")
    click.echo(f"Description: {task['description']}")
    click.echo(f"Priority: {task['priority']}")
    click.echo(f"Status: {task['status']}")
    click.echo(f"Agent: {task.get('agent', 'Not assigned')}")
    click.echo(f"Created: {task['created_at']}")
    if task.get('updated_at'):
        click.echo(f"Updated: {task['updated_at']}")