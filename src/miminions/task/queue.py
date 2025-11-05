"""
Task queue with priority scheduling and DAG dependency resolution.

Based on spec 004 requirements FR-002, FR-003, FR-010.
"""

import heapq
from typing import Optional
from collections import defaultdict, deque
from datetime import datetime
import uuid

from .models import Task, TaskStatus, TaskDependency
from .exceptions import (
    TaskQueueFullError,
    CyclicDependencyError,
    TaskNotFoundError,
    DependencyNotMetError,
    InvalidTaskStateError
)


class TaskQueue:
    """
    Priority queue managing pending and active tasks with dependency resolution.

    Per spec 004 data-model.md:237-286.
    """

    def __init__(self, name: str = "default", max_size: int = 1000):
        """
        Initialize a task queue.

        Args:
            name: Queue name (e.g., "default", "high-priority")
            max_size: Maximum pending tasks (prevents unbounded growth)
        """
        self.queue_id = str(uuid.uuid4())
        self.name = name
        self.max_size = max_size
        self.created_at = datetime.now()
        self.paused = False

        # Internal storage
        self._tasks: dict[str, Task] = {}  # task_id -> Task
        self._dependencies: dict[str, set[str]] = defaultdict(set)  # task_id -> set(depends_on_ids)
        self._dependents: dict[str, set[str]] = defaultdict(set)  # task_id -> set(dependent_ids)
        self._heap: list[tuple[int, str]] = []  # Min-heap of (priority, task_id) for ready tasks

    @property
    def pending_count(self) -> int:
        """Number of tasks with status=pending."""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.PENDING)

    @property
    def running_count(self) -> int:
        """Number of tasks with status=running."""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.RUNNING)

    @property
    def completed_count(self) -> int:
        """Number of tasks with status=completed."""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.COMPLETED)

    @property
    def failed_count(self) -> int:
        """Number of tasks with status=failed."""
        return sum(1 for t in self._tasks.values() if t.status == TaskStatus.FAILED)

    def enqueue(self, task: Task, dependencies: Optional[list[str]] = None) -> None:
        """
        Add task to queue.

        Args:
            task: Task to enqueue
            dependencies: List of task IDs this task depends on

        Raises:
            TaskQueueFullError: If queue is at capacity
            CyclicDependencyError: If dependencies would create a cycle
            TaskNotFoundError: If a dependency task doesn't exist
        """
        if self.pending_count >= self.max_size:
            raise TaskQueueFullError(self.name, self.max_size)

        # Validate dependencies exist
        dependencies = dependencies or []
        for dep_id in dependencies:
            if dep_id not in self._tasks:
                raise TaskNotFoundError(dep_id)

        # Check for cycles before adding
        if dependencies:
            self._validate_no_cycles(task.task_id, dependencies)

        # Add task
        self._tasks[task.task_id] = task

        # Add dependencies
        if dependencies:
            self._dependencies[task.task_id] = set(dependencies)
            for dep_id in dependencies:
                self._dependents[dep_id].add(task.task_id)

        # If no dependencies or all dependencies met, add to ready heap
        if self._is_ready(task.task_id):
            heapq.heappush(self._heap, (task.priority, task.task_id))

    def dequeue(self) -> Optional[Task]:
        """
        Get highest priority ready task (all dependencies met).

        Returns:
            Task if available, None if queue empty or paused

        Note: Does not remove task from queue, only marks it for assignment.
        """
        if self.paused:
            return None

        # Clean up heap (remove tasks that are no longer pending/ready)
        while self._heap:
            priority, task_id = heapq.heappop(self._heap)

            if task_id not in self._tasks:
                continue  # Task was removed

            task = self._tasks[task_id]

            if task.status != TaskStatus.PENDING:
                continue  # Task already started/completed

            if not self._is_ready(task_id):
                continue  # Dependencies changed

            return task

        return None

    def get_ready_tasks(self) -> list[Task]:
        """
        Return all tasks ready for execution (dependencies satisfied).

        Returns:
            List of tasks with status=pending and all dependencies completed
        """
        ready = []
        for task_id, task in self._tasks.items():
            if task.status == TaskStatus.PENDING and self._is_ready(task_id):
                ready.append(task)

        # Sort by priority (lower = higher priority)
        ready.sort(key=lambda t: t.priority)
        return ready

    def mark_completed(self, task_id: str) -> list[str]:
        """
        Mark task as completed and enqueue newly ready dependent tasks.

        Args:
            task_id: ID of completed task

        Returns:
            List of task IDs that became ready after this completion

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)

        task = self._tasks[task_id]
        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()

        # Find dependent tasks that are now ready
        newly_ready = []
        for dependent_id in self._dependents.get(task_id, set()):
            if self._is_ready(dependent_id):
                dependent_task = self._tasks[dependent_id]
                heapq.heappush(self._heap, (dependent_task.priority, dependent_id))
                newly_ready.append(dependent_id)

        return newly_ready

    def mark_failed(self, task_id: str, error_message: str) -> None:
        """
        Mark task as failed.

        Args:
            task_id: ID of failed task
            error_message: Error description

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)

        task = self._tasks[task_id]
        task.status = TaskStatus.FAILED
        task.error_message = error_message
        task.completed_at = datetime.now()

    def cancel_task(self, task_id: str) -> None:
        """
        Cancel a pending task.

        Args:
            task_id: ID of task to cancel

        Raises:
            TaskNotFoundError: If task doesn't exist
            InvalidTaskStateError: If task is not pending
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)

        task = self._tasks[task_id]
        if task.status != TaskStatus.PENDING:
            raise InvalidTaskStateError(task_id, task.status.value, "cancel")

        task.status = TaskStatus.CANCELLED

    def get_task(self, task_id: str) -> Task:
        """
        Get task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task object

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)
        return self._tasks[task_id]

    def get_dependencies(self, task_id: str) -> list[str]:
        """
        Get list of task IDs this task depends on.

        Args:
            task_id: Task identifier

        Returns:
            List of dependency task IDs

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        if task_id not in self._tasks:
            raise TaskNotFoundError(task_id)
        return list(self._dependencies.get(task_id, set()))

    def pause(self) -> None:
        """Pause queue (no new assignments until resumed)."""
        self.paused = True

    def resume(self) -> None:
        """Resume queue assignments."""
        self.paused = False

    def _is_ready(self, task_id: str) -> bool:
        """
        Check if task is ready for execution (all dependencies completed).

        Args:
            task_id: Task to check

        Returns:
            True if task has no dependencies or all are completed
        """
        if task_id not in self._dependencies:
            return True  # No dependencies

        for dep_id in self._dependencies[task_id]:
            if dep_id not in self._tasks:
                return False  # Dependency doesn't exist

            dep_task = self._tasks[dep_id]
            if dep_task.status != TaskStatus.COMPLETED:
                return False  # Dependency not completed

        return True

    def _validate_no_cycles(self, task_id: str, dependencies: list[str]) -> None:
        """
        Validate that adding dependencies won't create a cycle.

        Uses DFS to detect cycles in the dependency graph.

        Args:
            task_id: Task to add
            dependencies: Proposed dependencies

        Raises:
            CyclicDependencyError: If adding dependencies would create a cycle
        """
        # Build adjacency list with proposed edges
        graph = defaultdict(set)

        # Add existing edges
        for tid, deps in self._dependencies.items():
            graph[tid] = set(deps)

        # Add proposed edges
        graph[task_id] = set(dependencies)

        # DFS cycle detection
        visited = set()
        rec_stack = set()

        def has_cycle_dfs(node: str) -> bool:
            visited.add(node)
            rec_stack.add(node)

            for neighbor in graph.get(node, []):
                if neighbor not in visited:
                    if has_cycle_dfs(neighbor):
                        return True
                elif neighbor in rec_stack:
                    return True  # Back edge = cycle

            rec_stack.remove(node)
            return False

        # Check from the new task
        if has_cycle_dfs(task_id):
            raise CyclicDependencyError(task_id, dependencies[0])

    def __repr__(self) -> str:
        return (
            f"TaskQueue(name='{self.name}', "
            f"pending={self.pending_count}, "
            f"running={self.running_count}, "
            f"completed={self.completed_count})"
        )
