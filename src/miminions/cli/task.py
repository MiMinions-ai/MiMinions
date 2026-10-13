"""
Task management commands for MiMinions CLI.
"""
import json
import click
import uuid
from datetime import datetime, timezone
from miminions.core.paths import get_config_dir
from .persistence import load_json, save_json
from miminions.execution import ExecutionService
from miminions.execution.models import TERMINAL
from .dispatch import follow_task
# TODO(auth): Re-enable require_auth when task operations become account-backed.


def get_tasks_file():
    """Get the tasks configuration file path."""
    return get_config_dir() / "tasks.json"


def load_tasks():
    """Load tasks from configuration."""
    return load_json(get_tasks_file())


def save_tasks(tasks):
    """Save tasks to configuration."""
    save_json(get_tasks_file(), tasks)


def _load_agents():
    """Load agents from configuration for cross-reference checks."""
    agents_file = get_config_dir() / "agents.json"
    if not agents_file.exists():
        return {}

    with open(agents_file, "r") as f:
        return json.load(f)


def _validate_agent_reference_or_error(agent_id: str | None) -> bool:
    """Return True when agent reference is empty or exists; else print error."""
    if not agent_id:
        return True

    agents = _load_agents()
    if agent_id not in agents:
        click.echo(f"Agent '{agent_id}' not found.", err=True)
        return False
    return True


@click.group()
def task_cli():
    """Task management commands."""
    pass


@task_cli.command("list")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
@click.option("--kind", type=click.Choice(["all", "work_item", "execution"]), default="all")
# @require_auth  # TODO(auth): placeholder; local task operations do not require sign-in yet.
def list_tasks(as_json, kind="all"):
    """List all tasks."""
    tasks = load_tasks() if kind != "execution" else {}
    executions = ExecutionService(get_config_dir()).store.list() if kind != "work_item" else []

    if as_json:
        payload = [{"id": task_id, **task_data, "kind": "work_item"} for task_id, task_data in tasks.items()]
        payload.extend(task.to_dict() for task in executions)
        click.echo(json.dumps(payload, indent=2))
        return
    
    if not tasks and not executions:
        click.echo("No tasks configured.")
        return
    
    click.echo("Tasks:")
    for task_id, task_data in tasks.items():
        status = task_data.get("status", "pending")
        title = task_data.get("title", task_id)
        description = task_data.get("description", "No description")
        priority = task_data.get("priority", "medium")
        click.echo(f"  {task_id}: {title} (work_item, {status}, {priority}) - {description}")
    for task in executions:
        click.echo(f"  {task.id}: {task.request.kind} (execution, {task.status})")


@task_cli.command("add")
@click.option("--title", prompt="Task title", help="Title of the task")
@click.option("--description", prompt="Description", help="Description of the task")
@click.option("--priority", type=click.Choice(["low", "medium", "high"]), default="medium", help="Priority level")
@click.option("--agent", help="Agent ID to assign the task to")
# @require_auth  # TODO(auth): placeholder; local task operations do not require sign-in yet.
def add_task(title, description, priority, agent):
    """Add a new task."""
    if not _validate_agent_reference_or_error(agent):
        return

    tasks = load_tasks()
    
    task_id = str(uuid.uuid4())[:8]
    
    tasks[task_id] = {
        "title": title,
        "description": description,
        "priority": priority,
        "status": "pending",
        "agent": agent,
        "created_at": datetime.now(timezone.utc).isoformat(),
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
# @require_auth  # TODO(auth): placeholder; local task operations do not require sign-in yet.
def update_task(task_id, title, description, priority, status, agent):
    """Update an existing task."""
    if task_id.startswith("exec_"):
        raise click.ClickException("Execution task status is runtime-owned; use task cancel.")
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
        if not _validate_agent_reference_or_error(agent):
            return
        task["agent"] = agent
    
    task["updated_at"] = datetime.now(timezone.utc).isoformat()

    save_tasks(tasks)
    click.echo(f"Task '{task_id}' updated successfully")


@task_cli.command("remove")
@click.argument("task_id")
@click.confirmation_option(prompt="Are you sure you want to remove this task?")
# @require_auth  # TODO(auth): placeholder; local task operations do not require sign-in yet.
def remove_task(task_id):
    """Remove a task."""
    if task_id.startswith("exec_"):
        try:
            ExecutionService(get_config_dir()).store.remove(task_id)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"Task '{task_id}' removed successfully")
        return
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
# @require_auth  # TODO(auth): placeholder; local task operations do not require sign-in yet.
def duplicate_task(task_id, title):
    """Duplicate an existing task."""
    if task_id.startswith("exec_"):
        raise click.ClickException("Execution tasks cannot be duplicated. Submit a new operation explicitly.")
    tasks = load_tasks()
    
    if task_id not in tasks:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return
    
    original_task = tasks[task_id].copy()
    new_task_id = str(uuid.uuid4())[:8]
    
    if title:
        original_task["title"] = title
    else:
        original_task["title"] = f"{original_task['title']} (copy)"
    
    original_task["status"] = "pending"
    original_task["created_at"] = datetime.now(timezone.utc).isoformat()
    original_task["updated_at"] = None
    
    tasks[new_task_id] = original_task
    save_tasks(tasks)
    click.echo(f"Task duplicated successfully with ID: {new_task_id}")


@task_cli.command("show")
@click.argument("task_id")
@click.option("--json", "as_json", is_flag=True, help="Output machine-readable JSON.")
# @require_auth  # TODO(auth): placeholder; local task operations do not require sign-in yet.
def show_task(task_id, as_json):
    """Show detailed information about a task."""
    if task_id.startswith("exec_"):
        try:
            service = ExecutionService(get_config_dir())
            task = service.get(task_id)
        except ValueError as exc:
            raise click.ClickException(str(exc)) from exc
        if as_json:
            click.echo(json.dumps(task.to_dict(), indent=2))
        else:
            click.echo(f"Task ID: {task.id}\nKind: execution\nOperation: {task.request.kind}\nStatus: {task.status}\nCreated: {task.created_at}")
            for field, label in (("agent_id", "Agent"), ("workspace", "Workspace"), ("session_id", "Session"),
                                 ("tool_name", "Tool"), ("prompt", "Prompt")):
                if task.request.params.get(field):
                    click.echo(f"{label}: {task.request.params[field]}")
            if task.started_at:
                click.echo(f"Started: {task.started_at}")
            if task.ended_at:
                click.echo(f"Finished: {task.ended_at}")
            if task.result is not None:
                click.echo(f"Result: {task.result}")
            if task.error:
                click.echo(f"Error: {task.error}")
            if task.status == "waiting_for_input":
                for request in service.store.approvals(task_id):
                    click.echo(f"Approval: {request['id']} - {request['prompt']}")
        return
    tasks = load_tasks()
    
    if task_id not in tasks:
        click.echo(f"Task '{task_id}' not found.", err=True)
        return
    
    task = tasks[task_id]

    if as_json:
        payload = {"id": task_id, **task, "kind": "work_item"}
        click.echo(json.dumps(payload, indent=2))
        return
    
    click.echo(f"Task ID: {task_id}")
    click.echo("Kind: work_item")
    click.echo(f"Title: {task['title']}")
    click.echo(f"Description: {task['description']}")
    click.echo(f"Priority: {task['priority']}")
    click.echo(f"Status: {task['status']}")
    click.echo(f"Agent: {task.get('agent', 'Not assigned')}")
    click.echo(f"Created: {task['created_at']}")
    if task.get('updated_at'):
        click.echo(f"Updated: {task['updated_at']}")


@task_cli.command("tail")
@click.argument("task_id")
@click.option("--after", type=click.IntRange(min=0), default=0, help="Replay events after this sequence, then follow.")
@click.option("--json", "as_json", is_flag=True, help="Emit one JSON event per line; never prompt for approval.")
def tail_task(task_id, after, as_json):
    """Replay and follow an execution task until termination."""
    code = follow_task(ExecutionService(get_config_dir()), task_id, after=after, as_json=as_json)
    if code:
        raise click.exceptions.Exit(code)


@task_cli.command("cancel")
@click.argument("task_id")
def cancel_task(task_id):
    """Request cancellation of an execution task."""
    try:
        ExecutionService(get_config_dir()).cancel(task_id)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Cancellation requested for {task_id}.")


@task_cli.command("approve")
@click.argument("task_id")
@click.argument("request_id")
@click.option("--allow", is_flag=True)
@click.option("--deny", is_flag=True)
def approve_task(task_id, request_id, allow, deny):
    """Answer one pending execution approval request."""
    if allow == deny:
        raise click.UsageError("Specify exactly one of --allow or --deny.")
    try:
        ExecutionService(get_config_dir()).approve(task_id, request_id, allow)
    except ValueError as exc:
        raise click.ClickException(str(exc)) from exc
    click.echo(f"Approval {request_id} {'allowed' if allow else 'denied'}.")
