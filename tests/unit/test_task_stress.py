"""
Stress tests and edge cases for task module.

Tests performance limits, boundary conditions, and extreme scenarios.
"""

import pytest
from datetime import datetime
import uuid

from src.miminions.task import Task, TaskStatus, TaskPriority, TaskQueue, TaskRepository


@pytest.mark.stress
class TestQueueStress:
    """Stress tests for task queue."""

    def test_queue_with_max_capacity(self):
        """Test queue at maximum capacity."""
        queue = TaskQueue(max_size=1000)

        # Fill to capacity
        for i in range(1000):
            task = Task(
                task_id=str(i),
                name=f"Task {i}",
                status=TaskStatus.PENDING,
                created_at=datetime.now()
            )
            queue.enqueue(task)

        assert queue.pending_count == 1000

    @pytest.mark.slow
    def test_queue_with_many_priorities(self):
        """Test queue with many different priority levels."""
        queue = TaskQueue()

        # Create tasks with all priority levels 0-100
        for priority in range(101):
            task = Task(
                task_id=f"p-{priority}",
                name=f"Priority {priority}",
                priority=priority,
                status=TaskStatus.PENDING,
                created_at=datetime.now()
            )
            queue.enqueue(task)

        # Dequeue and verify ordering
        last_priority = -1
        for _ in range(101):
            task = queue.dequeue()
            assert task.priority >= last_priority
            last_priority = task.priority

    @pytest.mark.slow
    def test_queue_with_complex_dag(self):
        """Test queue with complex DAG (50 tasks, many dependencies)."""
        queue = TaskQueue()

        # Create 50 tasks
        tasks = []
        for i in range(50):
            task = Task(
                task_id=str(i),
                name=f"Task {i}",
                status=TaskStatus.PENDING,
                created_at=datetime.now()
            )
            tasks.append(task)

        # First task has no dependencies
        queue.enqueue(tasks[0])

        # Each task depends on previous two
        for i in range(1, 50):
            deps = []
            if i >= 1:
                deps.append(str(i-1))
            if i >= 2:
                deps.append(str(i-2))

            queue.enqueue(tasks[i], dependencies=deps)

        # Process all tasks in dependency order
        completed = 0
        while completed < 50:
            ready = queue.get_ready_tasks()
            if not ready:
                break

            for task in ready[:5]:  # Process up to 5 at a time
                queue.mark_completed(task.task_id)
                completed += 1

        assert completed == 50


@pytest.mark.stress
class TestRepositoryStress:
    """Stress tests for task repository."""

    @pytest.mark.slow
    def test_repository_with_many_tasks(self):
        """Test repository with 1000 tasks."""
        repo = TaskRepository(":memory:")

        # Save 1000 tasks
        for i in range(1000):
            task = Task(
                task_id=str(i),
                name=f"Task {i}",
                status=TaskStatus.PENDING,
                created_at=datetime.now()
            )
            repo.save_task(task)

        # Load all
        all_tasks = repo.load_all_tasks()
        assert len(all_tasks) == 1000

        repo.close()

    @pytest.mark.slow
    def test_repository_with_many_dependencies(self):
        """Test repository with many dependencies."""
        repo = TaskRepository(":memory:")

        # Create 100 tasks
        for i in range(100):
            task = Task(
                task_id=str(i),
                name=f"Task {i}",
                status=TaskStatus.PENDING,
                created_at=datetime.now()
            )
            repo.save_task(task)

        # Create 500 dependencies (each task depends on 5 random others)
        import random
        from src.miminions.task.models import TaskDependency

        for i in range(20, 100):
            # Each task depends on 5 random previous tasks
            for _ in range(5):
                dep_id = str(random.randint(0, i-1))
                try:
                    repo.save_dependency(TaskDependency(
                        task_id=str(i),
                        depends_on_task_id=dep_id
                    ))
                except:
                    pass  # Ignore duplicates

        # Verify dependencies saved
        deps = repo.load_dependencies("99")
        assert len(deps) > 0

        repo.close()

    def test_repository_with_large_json_data(self):
        """Test repository with large JSON data."""
        repo = TaskRepository(":memory:")

        # Create task with large input/output data
        large_data = {f"key_{i}": f"value_{i}" * 100 for i in range(100)}

        task = Task(
            task_id="large-data",
            name="Large Data Task",
            status=TaskStatus.COMPLETED,
            input_data=large_data,
            output_data=large_data,
            created_at=datetime.now()
        )

        repo.save_task(task)

        # Load and verify
        loaded = repo.load_task("large-data")
        assert len(loaded.input_data) == 100
        assert len(loaded.output_data) == 100

        repo.close()


@pytest.mark.stress
class TestEdgeCases:
    """Test extreme edge cases."""

    def test_task_id_with_special_characters(self):
        """Test task with special characters in ID."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        task = Task(
            task_id="task-!@#$%^&*()_+-=[]{}|;:',.<>?",
            name="Special ID",
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        queue.enqueue(task)
        repo.save_task(task)

        loaded = repo.load_task("task-!@#$%^&*()_+-=[]{}|;:',.<>?")
        assert loaded.name == "Special ID"

        repo.close()

    def test_task_name_with_newlines_and_tabs(self):
        """Test task name with newlines and tabs."""
        repo = TaskRepository(":memory:")

        task = Task(
            task_id="whitespace-test",
            name="Task\nwith\nnewlines\tand\ttabs",
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        repo.save_task(task)

        loaded = repo.load_task("whitespace-test")
        assert "\n" in loaded.name
        assert "\t" in loaded.name

        repo.close()

    def test_empty_input_and_output_data(self):
        """Test task with empty dicts for data."""
        repo = TaskRepository(":memory:")

        task = Task(
            task_id="empty-data",
            name="Empty Data",
            status=TaskStatus.COMPLETED,
            input_data={},
            output_data={},
            created_at=datetime.now()
        )

        repo.save_task(task)

        loaded = repo.load_task("empty-data")
        assert loaded.input_data == {}
        assert loaded.output_data == {}

        repo.close()

    def test_task_with_all_timestamps_same(self):
        """Test task with created, started, and completed at same time."""
        repo = TaskRepository(":memory:")

        now = datetime.now()
        task = Task(
            task_id="instant-task",
            name="Instant",
            status=TaskStatus.COMPLETED,
            created_at=now,
            started_at=now,
            completed_at=now,
            output_data={"instant": True}
        )

        repo.save_task(task)

        loaded = repo.load_task("instant-task")
        # Timestamps might have slight difference due to float conversion
        assert abs((loaded.created_at - loaded.started_at).total_seconds()) < 0.001
        assert abs((loaded.started_at - loaded.completed_at).total_seconds()) < 0.001

        repo.close()

    def test_queue_dequeue_same_task_twice(self):
        """Test dequeueing same task twice returns it once."""
        queue = TaskQueue()

        task = Task(
            task_id="once",
            name="Dequeue Once",
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        queue.enqueue(task)

        first = queue.dequeue()
        assert first is not None
        assert first.task_id == "once"

        # Mark as running so it's not dequeued again
        task.status = TaskStatus.RUNNING
        task.assigned_agent_id = "agent-1"

        second = queue.dequeue()
        # Should not get the same task again
        assert second is None or second.task_id != "once"

    def test_very_long_task_name(self):
        """Test task with 200 character name (max allowed)."""
        repo = TaskRepository(":memory:")

        long_name = "x" * 200
        task = Task(
            task_id="long-name",
            name=long_name,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        repo.save_task(task)

        loaded = repo.load_task("long-name")
        assert len(loaded.name) == 200

        repo.close()

    def test_zero_and_max_priority_boundary(self):
        """Test tasks with 0 and 100 priority."""
        queue = TaskQueue()

        task_high = Task(
            task_id="p0",
            name="Priority 0",
            priority=0,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        task_low = Task(
            task_id="p100",
            name="Priority 100",
            priority=100,
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        queue.enqueue(task_low)
        queue.enqueue(task_high)

        # Should get high priority first
        first = queue.dequeue()
        assert first.priority == 0

    def test_task_with_max_retries_zero(self):
        """Test task with max_retries=0 (no retries allowed)."""
        repo = TaskRepository(":memory:")

        task = Task(
            task_id="no-retry",
            name="No Retries",
            status=TaskStatus.PENDING,
            retry_count=0,
            max_retries=0,
            created_at=datetime.now()
        )

        repo.save_task(task)

        loaded = repo.load_task("no-retry")
        assert loaded.max_retries == 0
        assert loaded.retry_count == 0

        repo.close()

    def test_task_with_timeout_one_second(self):
        """Test task with minimum timeout (1 second)."""
        repo = TaskRepository(":memory:")

        task = Task(
            task_id="fast-timeout",
            name="Fast Timeout",
            status=TaskStatus.PENDING,
            timeout_seconds=1,
            created_at=datetime.now()
        )

        repo.save_task(task)

        loaded = repo.load_task("fast-timeout")
        assert loaded.timeout_seconds == 1

        repo.close()


@pytest.mark.stress
class TestConcurrency:
    """Test concurrent operations."""

    def test_multiple_repository_connections(self, temp_db_path):
        """Test multiple repository connections to same database."""
        # Create two connections
        repo1 = TaskRepository(temp_db_path)
        repo2 = TaskRepository(temp_db_path)

        task1 = Task(
            task_id="1",
            name="Task 1",
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        task2 = Task(
            task_id="2",
            name="Task 2",
            status=TaskStatus.PENDING,
            created_at=datetime.now()
        )

        # Save from different connections
        repo1.save_task(task1)
        repo2.save_task(task2)

        # Both should be able to read both tasks
        loaded1_from_repo1 = repo1.load_task("1")
        loaded2_from_repo1 = repo1.load_task("2")
        loaded1_from_repo2 = repo2.load_task("1")
        loaded2_from_repo2 = repo2.load_task("2")

        assert loaded1_from_repo1.task_id == "1"
        assert loaded2_from_repo1.task_id == "2"
        assert loaded1_from_repo2.task_id == "1"
        assert loaded2_from_repo2.task_id == "2"

        repo1.close()
        repo2.close()
