"""
Integration tests for task module.

Tests end-to-end workflows combining queue, repository,
and models together.
"""

import pytest
from datetime import datetime
import uuid
import tempfile
from pathlib import Path

from src.miminions.task import (
    Task,
    TaskStatus,
    TaskPriority,
    TaskQueue,
    TaskRepository,
    TaskDependency,
    TaskQueueFullError,
    CyclicDependencyError
)


def create_task(name="Test", priority=50, task_id=None, status=TaskStatus.PENDING):
    """Helper to create a task."""
    return Task(
        task_id=task_id or str(uuid.uuid4()),
        name=name,
        priority=priority,
        status=status,
        created_at=datetime.now()
    )


class TestQueueRepositoryIntegration:
    """Test queue and repository working together."""

    def test_enqueue_and_persist(self):
        """Test enqueueing task and persisting to database."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        task = create_task("Persist Task", task_id="persist-1")

        # Enqueue
        queue.enqueue(task)
        assert queue.pending_count == 1

        # Persist
        repo.save_task(task)

        # Load from DB
        loaded = repo.load_task("persist-1")
        assert loaded.name == "Persist Task"

        repo.close()

    def test_dequeue_process_and_update(self):
        """Test complete task lifecycle: enqueue -> dequeue -> process -> persist."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        # Create and enqueue task
        task = create_task("Process Task", task_id="process-1")
        queue.enqueue(task)
        repo.save_task(task)

        # Dequeue
        dequeued = queue.dequeue()
        assert dequeued is not None

        # Simulate processing: mark as running
        dequeued.status = TaskStatus.RUNNING
        dequeued.assigned_agent_id = "agent-123"
        repo.update_status(
            dequeued.task_id,
            TaskStatus.RUNNING,
            assigned_agent_id="agent-123"
        )

        # Complete processing
        queue.mark_completed(dequeued.task_id)
        repo.update_status(
            dequeued.task_id,
            TaskStatus.COMPLETED,
            output_data={"result": "success"}
        )

        # Verify final state in DB
        final = repo.load_task("process-1")
        assert final.status == TaskStatus.COMPLETED
        assert final.output_data == {"result": "success"}

        repo.close()

    def test_dependency_workflow_with_persistence(self):
        """Test task dependencies with persistence."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        # Create tasks
        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        task_c = create_task("Task C", task_id="c")

        # Persist all
        repo.save_task(task_a)
        repo.save_task(task_b)
        repo.save_task(task_c)

        # Enqueue with dependencies: c depends on a and b
        queue.enqueue(task_a)
        queue.enqueue(task_b)
        queue.enqueue(task_c, dependencies=["a", "b"])

        # Persist dependencies
        repo.save_dependency(TaskDependency(task_id="c", depends_on_task_id="a"))
        repo.save_dependency(TaskDependency(task_id="c", depends_on_task_id="b"))

        # Verify dependencies in DB
        deps = repo.load_dependencies("c")
        assert set(deps) == {"a", "b"}

        # Complete a
        queue.mark_completed("a")
        repo.update_status("a", TaskStatus.COMPLETED)

        # c should still not be ready
        ready = queue.get_ready_tasks()
        assert not any(t.task_id == "c" for t in ready)

        # Complete b
        queue.mark_completed("b")
        repo.update_status("b", TaskStatus.COMPLETED)

        # Now c should be ready
        ready = queue.get_ready_tasks()
        assert any(t.task_id == "c" for t in ready)

        repo.close()

    def test_queue_recovery_from_database(self):
        """Test reconstructing queue state from persisted database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "recovery.db"

            # Session 1: Create and persist tasks
            repo1 = TaskRepository(db_path)
            queue1 = TaskQueue()

            task1 = create_task("Task 1", priority=TaskPriority.HIGH, task_id="1")
            task2 = create_task("Task 2", priority=TaskPriority.LOW, task_id="2")
            task3 = create_task("Task 3", task_id="3", status=TaskStatus.COMPLETED)
            task3.output_data = {"done": True}

            queue1.enqueue(task1)
            queue1.enqueue(task2)

            repo1.save_task(task1)
            repo1.save_task(task2)
            repo1.save_task(task3)
            repo1.close()

            # Session 2: Recover from DB
            repo2 = TaskRepository(db_path)
            queue2 = TaskQueue()

            # Load all pending tasks
            pending_tasks = repo2.load_all_tasks(status=TaskStatus.PENDING)
            for task in pending_tasks:
                queue2.enqueue(task)

            # Verify queue state recovered
            assert queue2.pending_count == 2

            # Verify priority ordering maintained
            first = queue2.dequeue()
            assert first.task_id == "1"  # High priority

            repo2.close()


class TestCompleteWorkflows:
    """Test complete end-to-end workflows."""

    def test_multi_agent_task_distribution(self):
        """Test distributing tasks across multiple agents."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        # Create 10 tasks
        tasks = [create_task(f"Task {i}", task_id=str(i)) for i in range(10)]

        for task in tasks:
            queue.enqueue(task)
            repo.save_task(task)

        # Simulate 3 agents processing tasks
        agents = ["agent-1", "agent-2", "agent-3"]
        agent_tasks = {agent: [] for agent in agents}

        # Distribute tasks
        agent_idx = 0
        while True:
            task = queue.dequeue()
            if not task:
                break

            agent = agents[agent_idx % len(agents)]
            task.status = TaskStatus.RUNNING
            task.assigned_agent_id = agent
            agent_tasks[agent].append(task.task_id)

            repo.update_status(task.task_id, TaskStatus.RUNNING, assigned_agent_id=agent)
            agent_idx += 1

        # Verify distribution
        total_assigned = sum(len(tasks) for tasks in agent_tasks.values())
        assert total_assigned == 10

        # Each agent should have tasks
        for agent in agents:
            assert len(agent_tasks[agent]) > 0

        repo.close()

    def test_task_retry_workflow(self):
        """Test task retry workflow."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        # Create task with retries
        task = create_task("Retry Task", task_id="retry-1")
        task.max_retries = 3

        queue.enqueue(task)
        repo.save_task(task)

        # Simulate first failure
        task.status = TaskStatus.FAILED
        task.error_message = "Attempt 1 failed"
        task.retry_count = 1
        repo.save_task(task)

        # Retry: reset to pending
        task.status = TaskStatus.PENDING
        task.error_message = None
        repo.save_task(task)
        queue.enqueue(task)

        # Simulate second failure
        task.status = TaskStatus.FAILED
        task.error_message = "Attempt 2 failed"
        task.retry_count = 2
        repo.save_task(task)

        # Verify state
        loaded = repo.load_task("retry-1")
        assert loaded.retry_count == 2
        assert loaded.max_retries == 3
        assert loaded.retry_count < loaded.max_retries

        repo.close()

    def test_complex_dependency_graph_execution(self):
        """Test executing complex dependency graph."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        # Create graph:
        #     A
        #    / \
        #   B   C
        #    \ / \
        #     D   E
        #      \ /
        #       F

        tasks = {
            "a": create_task("Task A", task_id="a"),
            "b": create_task("Task B", task_id="b"),
            "c": create_task("Task C", task_id="c"),
            "d": create_task("Task D", task_id="d"),
            "e": create_task("Task E", task_id="e"),
            "f": create_task("Task F", task_id="f")
        }

        # Save all tasks
        for task in tasks.values():
            repo.save_task(task)

        # Create dependencies
        dependencies = [
            ("b", "a"),
            ("c", "a"),
            ("d", "b"),
            ("d", "c"),
            ("e", "c"),
            ("f", "d"),
            ("f", "e")
        ]

        # Enqueue with dependencies
        queue.enqueue(tasks["a"])

        queue.enqueue(tasks["b"], dependencies=["a"])
        queue.enqueue(tasks["c"], dependencies=["a"])

        queue.enqueue(tasks["d"], dependencies=["b", "c"])
        queue.enqueue(tasks["e"], dependencies=["c"])

        queue.enqueue(tasks["f"], dependencies=["d", "e"])

        # Persist dependencies
        for task_id, dep_id in dependencies:
            repo.save_dependency(TaskDependency(task_id=task_id, depends_on_task_id=dep_id))

        # Execute in order
        execution_order = []

        # Only a should be ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "a"
        execution_order.append("a")
        queue.mark_completed("a")

        # b and c should be ready
        ready = queue.get_ready_tasks()
        ready_ids = {t.task_id for t in ready}
        assert ready_ids == {"b", "c"}
        execution_order.extend(sorted(ready_ids))
        queue.mark_completed("b")
        queue.mark_completed("c")

        # d and e should be ready
        ready = queue.get_ready_tasks()
        ready_ids = {t.task_id for t in ready}
        assert ready_ids == {"d", "e"}
        execution_order.extend(sorted(ready_ids))
        queue.mark_completed("d")
        queue.mark_completed("e")

        # f should be ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].task_id == "f"
        execution_order.append("f")

        # Verify topological order
        assert execution_order == ["a", "b", "c", "d", "e", "f"]

        repo.close()

    def test_priority_with_dependencies(self):
        """Test priority ordering works with dependencies."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        # Create tasks:
        # - A (high priority, no deps)
        # - B (low priority, no deps)
        # - C (high priority, depends on B)

        task_a = create_task("Task A", priority=TaskPriority.HIGH, task_id="a")
        task_b = create_task("Task B", priority=TaskPriority.LOW, task_id="b")
        task_c = create_task("Task C", priority=TaskPriority.HIGH, task_id="c")

        for task in [task_a, task_b, task_c]:
            repo.save_task(task)

        queue.enqueue(task_a)
        queue.enqueue(task_b)
        queue.enqueue(task_c, dependencies=["b"])

        repo.save_dependency(TaskDependency(task_id="c", depends_on_task_id="b"))

        # Ready tasks should be a and b
        ready = queue.get_ready_tasks()
        ready_ids = [t.task_id for t in ready]
        # a should come first (higher priority)
        assert ready_ids == ["a", "b"]

        # Complete b
        queue.mark_completed("b")

        # Now c should be ready
        ready = queue.get_ready_tasks()
        assert any(t.task_id == "c" for t in ready)

        repo.close()


class TestErrorHandling:
    """Test error handling in integrated workflows."""

    def test_dependency_on_failed_task(self):
        """Test handling dependency on failed task."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")

        repo.save_task(task_a)
        repo.save_task(task_b)

        queue.enqueue(task_a)
        queue.enqueue(task_b, dependencies=["a"])

        # Mark a as failed
        queue.mark_failed("a", "Task failed")
        repo.update_status("a", TaskStatus.FAILED, error_message="Task failed")

        # b should still not be ready (dependency failed)
        ready = queue.get_ready_tasks()
        assert not any(t.task_id == "b" for t in ready)

        # Verify failure in DB
        loaded_a = repo.load_task("a")
        assert loaded_a.status == TaskStatus.FAILED
        assert loaded_a.error_message == "Task failed"

        repo.close()

    def test_queue_full_during_workflow(self):
        """Test handling queue full error during workflow."""
        queue = TaskQueue(max_size=2)
        repo = TaskRepository(":memory:")

        task1 = create_task("Task 1", task_id="1")
        task2 = create_task("Task 2", task_id="2")
        task3 = create_task("Task 3", task_id="3")

        repo.save_task(task1)
        repo.save_task(task2)
        repo.save_task(task3)

        queue.enqueue(task1)
        queue.enqueue(task2)

        # Should raise error
        with pytest.raises(TaskQueueFullError):
            queue.enqueue(task3)

        # Process one task to make space
        task1.status = TaskStatus.RUNNING
        task1.assigned_agent_id = "agent-1"

        # Now should be able to enqueue
        queue.enqueue(task3)
        assert queue.pending_count == 2  # task2 and task3

        repo.close()

    def test_cycle_prevention_with_persistence(self):
        """Test cycle prevention works with persistence."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")

        repo.save_task(task_a)
        repo.save_task(task_b)

        # Add both tasks to queue first  
        queue.enqueue(task_b)  # Add task B first (no dependencies)
        queue.enqueue(task_a, dependencies=["b"])  # Add task A with dependency on B
        
        # Save the dependency to repository
        repo.save_dependency(TaskDependency(task_id="a", depends_on_task_id="b"))

        # Try to create cycle: b->a (this should be detected by queue)
        with pytest.raises(CyclicDependencyError):
            # Try to update task B to depend on task A, which would create a cycle
            updated_task_b = create_task("Task B Updated", task_id="b")
            queue.enqueue(updated_task_b, dependencies=["a"])

        # Verify cycle not persisted
        deps_b = repo.load_dependencies("b")
        assert "a" not in deps_b

        repo.close()


class TestPerformanceWorkflows:
    """Test performance with larger datasets."""

    def test_hundred_tasks_workflow(self):
        """Test workflow with 100 tasks."""
        queue = TaskQueue(max_size=200)
        repo = TaskRepository(":memory:")

        # Create 100 tasks with random priorities
        import random
        tasks = []
        for i in range(100):
            priority = random.randint(0, 100)
            task = create_task(f"Task {i}", priority=priority, task_id=str(i))
            tasks.append(task)
            repo.save_task(task)
            queue.enqueue(task)

        assert queue.pending_count == 100

        # Process all tasks
        processed = 0
        while True:
            task = queue.dequeue()
            if not task:
                break

            queue.mark_completed(task.task_id)
            repo.update_status(task.task_id, TaskStatus.COMPLETED)
            processed += 1

        assert processed == 100
        assert queue.completed_count == 100

        repo.close()

    def test_deep_dependency_chain(self):
        """Test deep dependency chain (20 tasks)."""
        queue = TaskQueue()
        repo = TaskRepository(":memory:")

        # Create chain: 0 -> 1 -> 2 -> ... -> 19
        tasks = [create_task(f"Task {i}", task_id=str(i)) for i in range(20)]

        for i, task in enumerate(tasks):
            repo.save_task(task)

            if i == 0:
                queue.enqueue(task)
            else:
                queue.enqueue(task, dependencies=[str(i-1)])
                repo.save_dependency(TaskDependency(
                    task_id=str(i),
                    depends_on_task_id=str(i-1)
                ))

        # Process chain
        for i in range(20):
            ready = queue.get_ready_tasks()
            assert len(ready) == 1
            assert ready[0].task_id == str(i)

            queue.mark_completed(str(i))
            repo.update_status(str(i), TaskStatus.COMPLETED)

        assert queue.completed_count == 20

        repo.close()
