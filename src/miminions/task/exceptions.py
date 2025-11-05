"""
Task-specific exceptions for the multi-agent runtime system.

Based on spec 004 requirements and edge cases.
"""


class TaskError(Exception):
    """Base exception for all task-related errors."""
    pass


class TaskNotFoundError(TaskError):
    """Raised when a task ID cannot be found."""
    def __init__(self, task_id: str):
        self.task_id = task_id
        super().__init__(f"Task not found: {task_id}")


class TaskQueueFullError(TaskError):
    """Raised when attempting to enqueue to a full queue."""
    def __init__(self, queue_name: str, max_size: int):
        self.queue_name = queue_name
        self.max_size = max_size
        super().__init__(f"Queue '{queue_name}' is full (max size: {max_size})")


class CyclicDependencyError(TaskError):
    """Raised when a task dependency would create a cycle in the DAG."""
    def __init__(self, task_id: str, depends_on_task_id: str):
        self.task_id = task_id
        self.depends_on_task_id = depends_on_task_id
        super().__init__(
            f"Adding dependency {task_id} -> {depends_on_task_id} would create a cycle"
        )


class InvalidTaskStateError(TaskError):
    """Raised when a task operation is invalid for the current state."""
    def __init__(self, task_id: str, current_status: str, operation: str):
        self.task_id = task_id
        self.current_status = current_status
        self.operation = operation
        super().__init__(
            f"Cannot {operation} task {task_id} with status {current_status}"
        )


class TaskTimeoutError(TaskError):
    """Raised when a task exceeds its timeout duration."""
    def __init__(self, task_id: str, timeout_seconds: int):
        self.task_id = task_id
        self.timeout_seconds = timeout_seconds
        super().__init__(
            f"Task {task_id} exceeded timeout of {timeout_seconds} seconds"
        )


class DependencyNotMetError(TaskError):
    """Raised when attempting to start a task with unmet dependencies."""
    def __init__(self, task_id: str, unmet_dependencies: list[str]):
        self.task_id = task_id
        self.unmet_dependencies = unmet_dependencies
        super().__init__(
            f"Task {task_id} has unmet dependencies: {', '.join(unmet_dependencies)}"
        )


class MaxRetriesExceededError(TaskError):
    """Raised when a task has exceeded its maximum retry count."""
    def __init__(self, task_id: str, max_retries: int):
        self.task_id = task_id
        self.max_retries = max_retries
        super().__init__(
            f"Task {task_id} exceeded maximum retries ({max_retries})"
        )
