"""
Task module for the multi-agent runtime system.

Provides task models, queue management, persistence, and CLI commands.
Based on spec 004 (Multi-Agent Runtime System).

Public API:
    Models:
        - Task: Task entity with validation
        - TaskStatus: Task execution state enum
        - TaskDependency: Task dependency relationship
        - TaskPriority: Priority level constants

    Queue:
        - TaskQueue: Priority queue with DAG dependency resolution

    Persistence:
        - TaskRepository: SQLite persistence layer

    Exceptions:
        - TaskError: Base exception
        - TaskNotFoundError: Task not found
        - TaskQueueFullError: Queue at capacity
        - CyclicDependencyError: Dependency cycle detected
        - InvalidTaskStateError: Invalid state transition
        - TaskTimeoutError: Task timeout exceeded
        - DependencyNotMetError: Unmet dependencies
        - MaxRetriesExceededError: Retry limit exceeded

Usage Example:
    ```python
    from miminions.task import Task, TaskQueue, TaskRepository, TaskPriority

    # Create a task
    task = Task(
        task_id="123",
        name="Process data",
        priority=TaskPriority.HIGH,
        input_data={"file": "data.csv"}
    )

    # Use queue
    queue = TaskQueue(name="default", max_size=1000)
    queue.enqueue(task)

    # Persist to database
    with TaskRepository("tasks.db") as repo:
        repo.save_task(task)
    ```
"""

# Models
from .models import Task, TaskStatus, TaskDependency, TaskPriority

# Queue
from .queue import TaskQueue

# Persistence
from .repository import TaskRepository

# Exceptions
from .exceptions import (
    TaskError,
    TaskNotFoundError,
    TaskQueueFullError,
    CyclicDependencyError,
    InvalidTaskStateError,
    TaskTimeoutError,
    DependencyNotMetError,
    MaxRetriesExceededError
)

# CLI (not exported in public API, used internally)
# from .cli import task_cli

__all__ = [
    # Models
    "Task",
    "TaskStatus",
    "TaskDependency",
    "TaskPriority",
    # Queue
    "TaskQueue",
    # Persistence
    "TaskRepository",
    # Exceptions
    "TaskError",
    "TaskNotFoundError",
    "TaskQueueFullError",
    "CyclicDependencyError",
    "InvalidTaskStateError",
    "TaskTimeoutError",
    "DependencyNotMetError",
    "MaxRetriesExceededError",
]

__version__ = "0.1.0"
