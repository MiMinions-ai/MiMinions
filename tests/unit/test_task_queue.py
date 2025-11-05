"""
Unit tests for task queue.

Tests TaskQueue including priority scheduling, DAG dependency resolution,
state management, and cycle detection.
"""

import pytest
from datetime import datetime
import uuid

from src.miminions.task.models import Task, TaskStatus, TaskPriority
from src.miminions.task.queue import TaskQueue
from src.miminions.task.exceptions import (
    TaskQueueFullError,
    CyclicDependencyError,
    TaskNotFoundError,
    InvalidTaskStateError
)


def create_task(name="Test", priority=50, task_id=None):
    """Helper to create a task."""
    return Task(
        task_id=task_id or str(uuid.uuid4()),
        name=name,
        priority=priority,
        status=TaskStatus.PENDING,
        created_at=datetime.now()
    )


class TestTaskQueueBasics:
    """Test basic TaskQueue functionality."""

    def test_queue_creation(self):
        """Test creating a task queue."""
        queue = TaskQueue(name="test-queue", max_size=100)
        assert queue.name == "test-queue"
        assert queue.max_size == 100
        assert queue.pending_count == 0
        assert queue.paused == False

    def test_queue_default_parameters(self):
        """Test queue creation with default parameters."""
        queue = TaskQueue()
        assert queue.name == "default"
        assert queue.max_size == 1000

    def test_queue_has_uuid(self):
        """Test queue gets assigned a UUID."""
        queue = TaskQueue()
        assert queue.queue_id is not None
        # Check it's a valid UUID format
        uuid.UUID(queue.queue_id)

    def test_enqueue_task(self):
        """Test enqueueing a task."""
        queue = TaskQueue()
        task = create_task("Task 1")

        queue.enqueue(task)
        assert queue.pending_count == 1

    def test_dequeue_task(self):
        """Test dequeueing a task."""
        queue = TaskQueue()
        task = create_task("Task 1")

        queue.enqueue(task)
        dequeued = queue.dequeue()

        assert dequeued is not None
        assert dequeued.task_id == task.task_id
        assert dequeued.name == "Task 1"

    def test_dequeue_empty_queue(self):
        """Test dequeueing from empty queue returns None."""
        queue = TaskQueue()
        dequeued = queue.dequeue()
        assert dequeued is None

    def test_multiple_enqueue_dequeue(self):
        """Test multiple enqueue and dequeue operations."""
        queue = TaskQueue()
        task1 = create_task("Task 1")
        task2 = create_task("Task 2")

        queue.enqueue(task1)
        queue.enqueue(task2)

        assert queue.pending_count == 2

        dequeued1 = queue.dequeue()
        assert dequeued1 is not None
        assert queue.pending_count == 2  # Still 2 (dequeue doesn't remove from internal storage)


class TestQueuePriority:
    """Test priority-based task scheduling."""

    def test_high_priority_first(self):
        """Test higher priority tasks dequeued first."""
        queue = TaskQueue()

        low_task = create_task("Low", priority=TaskPriority.LOW)
        high_task = create_task("High", priority=TaskPriority.HIGH)
        medium_task = create_task("Medium", priority=TaskPriority.MEDIUM)

        # Enqueue in random order
        queue.enqueue(low_task)
        queue.enqueue(high_task)
        queue.enqueue(medium_task)

        # Should dequeue in priority order (high, medium, low)
        first = queue.dequeue()
        assert first.name == "High"

    def test_priority_ordering_multiple_tasks(self):
        """Test priority ordering with multiple tasks."""
        queue = TaskQueue()

        tasks = [
            create_task("P100", priority=100),
            create_task("P0", priority=0),
            create_task("P50", priority=50),
            create_task("P25", priority=25),
            create_task("P75", priority=75)
        ]

        for task in tasks:
            queue.enqueue(task)

        # Dequeue should give: P0, P25, P50, P75, P100
        dequeued_names = []
        for _ in range(5):
            task = queue.dequeue()
            if task:
                dequeued_names.append(task.name)

        assert dequeued_names == ["P0", "P25", "P50", "P75", "P100"]

    def test_same_priority_fifo(self):
        """Test tasks with same priority follow FIFO order."""
        queue = TaskQueue()

        task1 = create_task("Task 1", priority=50)
        task2 = create_task("Task 2", priority=50)
        task3 = create_task("Task 3", priority=50)

        queue.enqueue(task1)
        queue.enqueue(task2)
        queue.enqueue(task3)

        # Should maintain insertion order for same priority
        first = queue.dequeue()
        assert first.name == "Task 1"


class TestQueueCapacity:
    """Test queue capacity and overflow handling."""

    def test_queue_full_error(self):
        """Test enqueueing to full queue raises error."""
        queue = TaskQueue(max_size=2)

        task1 = create_task("Task 1")
        task2 = create_task("Task 2")
        task3 = create_task("Task 3")

        queue.enqueue(task1)
        queue.enqueue(task2)

        with pytest.raises(TaskQueueFullError) as exc_info:
            queue.enqueue(task3)

        assert exc_info.value.max_size == 2

    def test_queue_at_exactly_max_size(self):
        """Test queue accepts tasks up to max_size."""
        queue = TaskQueue(max_size=3)

        for i in range(3):
            queue.enqueue(create_task(f"Task {i}"))

        assert queue.pending_count == 3

    def test_queue_capacity_after_status_change(self):
        """Test queue capacity only counts pending tasks."""
        queue = TaskQueue(max_size=2)

        task1 = create_task("Task 1")
        task2 = create_task("Task 2")

        queue.enqueue(task1)
        queue.enqueue(task2)

        # Change task1 status to running
        task1.status = TaskStatus.RUNNING
        task1.assigned_agent_id = "agent-1"

        # Should allow new task since only 1 is pending
        task3 = create_task("Task 3")
        queue.enqueue(task3)

        assert queue.pending_count == 2  # task2 and task3


class TestQueueDependencies:
    """Test dependency management and DAG resolution."""

    def test_enqueue_with_dependency(self):
        """Test enqueueing task with dependency."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")

        queue.enqueue(task_a)
        queue.enqueue(task_b, dependencies=["a"])

        deps = queue.get_dependencies("b")
        assert "a" in deps

    def test_task_not_ready_with_pending_dependency(self):
        """Test task with pending dependency is not ready."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")

        queue.enqueue(task_a)
        queue.enqueue(task_b, dependencies=["a"])

        # Only task_a should be ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "a"

    def test_task_ready_after_dependency_completed(self):
        """Test task becomes ready after dependency completes."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")

        queue.enqueue(task_a)
        queue.enqueue(task_b, dependencies=["a"])

        # Complete task_a
        newly_ready = queue.mark_completed("a")

        # task_b should now be ready
        assert "b" in newly_ready
        ready = queue.get_ready_tasks()
        assert any(t.task_id == "b" for t in ready)

    def test_multiple_dependencies(self):
        """Test task with multiple dependencies."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        task_c = create_task("Task C", task_id="c")

        queue.enqueue(task_a)
        queue.enqueue(task_b)
        queue.enqueue(task_c, dependencies=["a", "b"])

        # task_c should not be ready
        ready = queue.get_ready_tasks()
        assert not any(t.task_id == "c" for t in ready)

        # Complete task_a only
        queue.mark_completed("a")
        ready = queue.get_ready_tasks()
        assert not any(t.task_id == "c" for t in ready)

        # Complete task_b
        queue.mark_completed("b")
        ready = queue.get_ready_tasks()
        assert any(t.task_id == "c" for t in ready)

    def test_dependency_chain(self):
        """Test chain of dependencies (A -> B -> C -> D)."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        task_c = create_task("Task C", task_id="c")
        task_d = create_task("Task D", task_id="d")

        queue.enqueue(task_a)
        queue.enqueue(task_b, dependencies=["a"])
        queue.enqueue(task_c, dependencies=["b"])
        queue.enqueue(task_d, dependencies=["c"])

        # Only a should be ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "a"

        # Complete chain
        queue.mark_completed("a")
        ready = queue.get_ready_tasks()
        assert any(t.task_id == "b" for t in ready)

        queue.mark_completed("b")
        ready = queue.get_ready_tasks()
        assert any(t.task_id == "c" for t in ready)

        queue.mark_completed("c")
        ready = queue.get_ready_tasks()
        assert any(t.task_id == "d" for t in ready)

    def test_diamond_dependency(self):
        """Test diamond dependency pattern (A -> B,C -> D)."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        task_c = create_task("Task C", task_id="c")
        task_d = create_task("Task D", task_id="d")

        queue.enqueue(task_a)
        queue.enqueue(task_b, dependencies=["a"])
        queue.enqueue(task_c, dependencies=["a"])
        queue.enqueue(task_d, dependencies=["b", "c"])

        # Complete a
        queue.mark_completed("a")

        # Both b and c should be ready
        ready = queue.get_ready_tasks()
        ready_ids = {t.task_id for t in ready}
        assert "b" in ready_ids
        assert "c" in ready_ids

        # Complete b only
        queue.mark_completed("b")
        ready = queue.get_ready_tasks()
        assert not any(t.task_id == "d" for t in ready)

        # Complete c
        queue.mark_completed("c")
        ready = queue.get_ready_tasks()
        assert any(t.task_id == "d" for t in ready)


class TestCycleDetection:
    """Test cycle detection in dependency graphs."""

    def test_direct_cycle(self):
        """Test detection of direct cycle (A -> B -> A)."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")

        queue.enqueue(task_a, dependencies=["b"])

        with pytest.raises(CyclicDependencyError):
            queue.enqueue(task_b, dependencies=["a"])

    def test_self_dependency_prevented_by_model(self):
        """Test self-dependency prevented at model level."""
        queue = TaskQueue()
        task_a = create_task("Task A", task_id="a")
        queue.enqueue(task_a)

        # Self-dependency should be caught by TaskDependency model
        # But queue should handle it gracefully
        with pytest.raises((CyclicDependencyError, ValueError)):
            queue.enqueue(task_a, dependencies=["a"])

    def test_indirect_cycle(self):
        """Test detection of indirect cycle (A -> B -> C -> A)."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        task_c = create_task("Task C", task_id="c")

        queue.enqueue(task_a, dependencies=["c"])
        queue.enqueue(task_b, dependencies=["a"])

        with pytest.raises(CyclicDependencyError):
            queue.enqueue(task_c, dependencies=["b"])

    def test_complex_cycle(self):
        """Test detection of complex cycle in larger graph."""
        queue = TaskQueue()

        for i in range(5):
            task = create_task(f"Task {i}", task_id=str(i))
            if i == 0:
                queue.enqueue(task)
            else:
                queue.enqueue(task, dependencies=[str(i-1)])

        # Try to create cycle: 4 -> 0
        task_5 = create_task("Task 5", task_id="5")
        with pytest.raises(CyclicDependencyError):
            queue.enqueue(task_5, dependencies=["4", "0"])  # Would create cycle


class TestQueueStateManagement:
    """Test task state management in queue."""

    def test_get_task(self):
        """Test getting task by ID."""
        queue = TaskQueue()
        task = create_task("Test", task_id="123")
        queue.enqueue(task)

        retrieved = queue.get_task("123")
        assert retrieved.task_id == "123"
        assert retrieved.name == "Test"

    def test_get_nonexistent_task(self):
        """Test getting nonexistent task raises error."""
        queue = TaskQueue()
        with pytest.raises(TaskNotFoundError):
            queue.get_task("nonexistent")

    def test_mark_failed(self):
        """Test marking task as failed."""
        queue = TaskQueue()
        task = create_task("Test", task_id="123")
        queue.enqueue(task)

        queue.mark_failed("123", "Error occurred")

        updated = queue.get_task("123")
        assert updated.status == TaskStatus.FAILED
        assert updated.error_message == "Error occurred"
        assert updated.completed_at is not None

    def test_cancel_task(self):
        """Test cancelling a pending task."""
        queue = TaskQueue()
        task = create_task("Test", task_id="123")
        queue.enqueue(task)

        queue.cancel_task("123")

        updated = queue.get_task("123")
        assert updated.status == TaskStatus.CANCELLED

    def test_cancel_running_task_fails(self):
        """Test cancelling running task raises error."""
        queue = TaskQueue()
        task = create_task("Test", task_id="123")
        task.status = TaskStatus.RUNNING
        task.assigned_agent_id = "agent-1"
        queue._tasks[task.task_id] = task

        with pytest.raises(InvalidTaskStateError):
            queue.cancel_task("123")

    def test_pending_count(self):
        """Test pending_count property."""
        queue = TaskQueue()

        task1 = create_task("Task 1")
        task2 = create_task("Task 2")
        queue.enqueue(task1)
        queue.enqueue(task2)

        assert queue.pending_count == 2

        task1.status = TaskStatus.RUNNING
        task1.assigned_agent_id = "agent-1"
        assert queue.pending_count == 1

    def test_running_count(self):
        """Test running_count property."""
        queue = TaskQueue()

        task = create_task("Test")
        queue.enqueue(task)
        assert queue.running_count == 0

        task.status = TaskStatus.RUNNING
        task.assigned_agent_id = "agent-1"
        assert queue.running_count == 1

    def test_completed_count(self):
        """Test completed_count property."""
        queue = TaskQueue()

        task = create_task("Test", task_id="123")
        queue.enqueue(task)
        assert queue.completed_count == 0

        queue.mark_completed("123")
        assert queue.completed_count == 1

    def test_failed_count(self):
        """Test failed_count property."""
        queue = TaskQueue()

        task = create_task("Test", task_id="123")
        queue.enqueue(task)
        assert queue.failed_count == 0

        queue.mark_failed("123", "Error")
        assert queue.failed_count == 1


class TestQueuePauseResume:
    """Test queue pause and resume functionality."""

    def test_pause_queue(self):
        """Test pausing queue."""
        queue = TaskQueue()
        queue.pause()
        assert queue.paused == True

    def test_resume_queue(self):
        """Test resuming queue."""
        queue = TaskQueue()
        queue.pause()
        queue.resume()
        assert queue.paused == False

    def test_dequeue_when_paused(self):
        """Test dequeue returns None when paused."""
        queue = TaskQueue()
        task = create_task("Test")
        queue.enqueue(task)

        queue.pause()
        dequeued = queue.dequeue()
        assert dequeued is None

    def test_dequeue_after_resume(self):
        """Test dequeue works after resume."""
        queue = TaskQueue()
        task = create_task("Test")
        queue.enqueue(task)

        queue.pause()
        queue.resume()

        dequeued = queue.dequeue()
        assert dequeued is not None


class TestQueueEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_enqueue_task_with_nonexistent_dependency(self):
        """Test enqueueing with nonexistent dependency raises error."""
        queue = TaskQueue()
        task = create_task("Test")

        with pytest.raises(TaskNotFoundError):
            queue.enqueue(task, dependencies=["nonexistent"])

    def test_get_dependencies_nonexistent_task(self):
        """Test getting dependencies for nonexistent task."""
        queue = TaskQueue()

        with pytest.raises(TaskNotFoundError):
            queue.get_dependencies("nonexistent")

    def test_get_dependencies_task_with_no_dependencies(self):
        """Test getting dependencies for task with none."""
        queue = TaskQueue()
        task = create_task("Test", task_id="123")
        queue.enqueue(task)

        deps = queue.get_dependencies("123")
        assert deps == []

    def test_empty_dependencies_list(self):
        """Test enqueueing with empty dependencies list."""
        queue = TaskQueue()
        task = create_task("Test")
        queue.enqueue(task, dependencies=[])

        ready = queue.get_ready_tasks()
        assert any(t.task_id == task.task_id for t in ready)

    def test_queue_repr(self):
        """Test queue string representation."""
        queue = TaskQueue(name="test-queue")
        task1 = create_task("Task 1", task_id="1")
        task2 = create_task("Task 2", task_id="2")

        queue.enqueue(task1)
        queue.enqueue(task2)
        queue.mark_completed("1")

        repr_str = repr(queue)
        assert "test-queue" in repr_str
        assert "pending" in repr_str.lower()
        assert "completed" in repr_str.lower()

    def test_large_number_of_tasks(self):
        """Test queue with many tasks."""
        queue = TaskQueue(max_size=1000)

        tasks = [create_task(f"Task {i}", priority=i % 100) for i in range(500)]

        for task in tasks:
            queue.enqueue(task)

        assert queue.pending_count == 500

    def test_dequeue_maintains_priority_with_many_tasks(self):
        """Test dequeue maintains priority order with many tasks."""
        queue = TaskQueue()

        # Add 100 tasks with random priorities
        import random
        priorities = list(range(100))
        random.shuffle(priorities)

        for i, priority in enumerate(priorities):
            queue.enqueue(create_task(f"Task {i}", priority=priority))

        # Dequeue all and verify ordering
        last_priority = -1
        for _ in range(100):
            task = queue.dequeue()
            if task:
                assert task.priority >= last_priority
                last_priority = task.priority


class TestGetReadyTasks:
    """Test get_ready_tasks functionality."""

    def test_get_ready_tasks_empty_queue(self):
        """Test get_ready_tasks on empty queue."""
        queue = TaskQueue()
        ready = queue.get_ready_tasks()
        assert ready == []

    def test_get_ready_tasks_all_ready(self):
        """Test get_ready_tasks when all tasks ready."""
        queue = TaskQueue()

        task1 = create_task("Task 1")
        task2 = create_task("Task 2")
        queue.enqueue(task1)
        queue.enqueue(task2)

        ready = queue.get_ready_tasks()
        assert len(ready) == 2

    def test_get_ready_tasks_sorted_by_priority(self):
        """Test get_ready_tasks returns sorted by priority."""
        queue = TaskQueue()

        queue.enqueue(create_task("Low", priority=100))
        queue.enqueue(create_task("High", priority=0))
        queue.enqueue(create_task("Medium", priority=50))

        ready = queue.get_ready_tasks()
        assert ready[0].name == "High"
        assert ready[1].name == "Medium"
        assert ready[2].name == "Low"

    def test_get_ready_tasks_excludes_blocked(self):
        """Test get_ready_tasks excludes tasks with unmet dependencies."""
        queue = TaskQueue()

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        queue.enqueue(task_a)
        queue.enqueue(task_b, dependencies=["a"])

        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "a"

    def test_get_ready_tasks_excludes_non_pending(self):
        """Test get_ready_tasks excludes non-pending tasks."""
        queue = TaskQueue()

        task1 = create_task("Task 1")
        task2 = create_task("Task 2")
        queue.enqueue(task1)
        queue.enqueue(task2)

        task1.status = TaskStatus.RUNNING
        task1.assigned_agent_id = "agent-1"

        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == task2.task_id
