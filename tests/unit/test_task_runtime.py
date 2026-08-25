"""Unit tests for task.control module (TaskRuntime)."""
import asyncio
from datetime import UTC, datetime
from unittest.mock import MagicMock

import pytest

from miminions.task.control import TaskRuntime
from miminions.task.model import AgentTask, TaskPriority, TaskStatus


class TaskRuntimeTestError(Exception):
    """Test-only exception raised by mock task agents."""


class TestTaskRuntimeInitialization:
    """Test TaskRuntime initialization."""

    def test_task_runtime_creation(self):
        """Test creating a TaskRuntime instance."""
        runtime = TaskRuntime()
        
        assert runtime.loop is None, f"expect runtime.loop is None, got {runtime.loop}"
        assert runtime.tasks == {}, f"expect runtime.tasks is empty {{}}, got {runtime.tasks}"
        assert runtime.status == TaskStatus.INITIALIZED, f"expect runtime.status is {TaskStatus.INITIALIZED}, got {runtime.status}"
        assert isinstance(runtime.last_update, datetime), f"expect the runtime.last_update to be a datetime instance, got {type(runtime.last_update)}"

    def test_task_runtime_initial_status(self):
        """Test TaskRuntime initial status is INITIALIZED."""
        runtime = TaskRuntime()
        assert runtime.status == TaskStatus.INITIALIZED, f"expect runtime.status is {TaskStatus.INITIALIZED}, got {runtime.status}"

    def test_task_runtime_initial_tasks_empty(self):
        """Test TaskRuntime starts with empty tasks dict."""
        runtime = TaskRuntime()
        assert len(runtime.tasks) == 0, f"expect runtime.tasks to be empty, got {len(runtime.tasks)}"
        assert isinstance(runtime.tasks, dict), f"expect runtime.tasks to be a dict instance, got {type(runtime.tasks)}"


class TestTaskRuntimeAddTask:
    """Test TaskRuntime add_task method."""

    def test_add_single_task(self):
        """Test adding a single task to runtime."""
        runtime = TaskRuntime()
        task = AgentTask(name="Test Task")
        
        runtime.add_task(task)
        
        assert len(runtime.tasks) == 1, f"expect runtime.tasks to have 1 task, got {len(runtime.tasks)}"
        assert task.id in runtime.tasks, f"expect runtime.tasks to contain {task.id}, got {runtime.tasks}"
        assert runtime.tasks[task.id] == task, f"expect runtime.tasks[task.id] to be {task}, got {runtime.tasks[task.id]}"
        assert runtime.status == TaskStatus.IDLE, f"expect runtime.status is {TaskStatus.IDLE}, got {runtime.status}"

    def test_add_multiple_tasks(self):
        """Test adding multiple tasks to runtime."""
        runtime = TaskRuntime()
        task1 = AgentTask(name="Task 1")
        task2 = AgentTask(name="Task 2")
        task3 = AgentTask(name="Task 3")
        
        runtime.add_task(task1)
        runtime.add_task(task2)
        runtime.add_task(task3)
        
        assert len(runtime.tasks) == 3, f"expect runtime.tasks to have 3 tasks, got {len(runtime.tasks)}"
        assert task1.id in runtime.tasks, f"expect runtime.tasks to contain {task1.id}, got {runtime.tasks}"
        assert task2.id in runtime.tasks, f"expect runtime.tasks to contain {task2.id}, got {runtime.tasks}"
        assert task3.id in runtime.tasks, f"expect runtime.tasks to contain {task3.id}, got {runtime.tasks}"

    def test_add_task_updates_status(self):
        """Test that adding a task updates runtime status to IDLE."""
        runtime = TaskRuntime()
        assert runtime.status == TaskStatus.INITIALIZED, f"expect runtime.status is {TaskStatus.INITIALIZED}, got {runtime.status}"
        
        task = AgentTask()
        runtime.add_task(task)
        
        assert runtime.status == TaskStatus.IDLE, f"expect runtime.status is {TaskStatus.IDLE}, got {runtime.status}"

    def test_add_task_updates_last_update(self):
        """Test that adding a task updates last_update timestamp."""
        runtime = TaskRuntime()
        initial_update = runtime.last_update
        
        # Small delay to ensure timestamp difference
        import time
        time.sleep(0.01)
        
        task = AgentTask()
        runtime.add_task(task)
        
        assert runtime.last_update > initial_update, f"expect runtime.last_update > initial_update, got {runtime.last_update}"

    def test_add_task_with_custom_id(self):
        """Test adding a task with a custom ID."""
        runtime = TaskRuntime()
        task = AgentTask(id="custom-id-123")
        
        runtime.add_task(task)
        
        assert "custom-id-123" in runtime.tasks, f"expect runtime.tasks to contain 'custom-id-123', got {runtime.tasks}"
        assert runtime.tasks["custom-id-123"] == task, f"expect runtime.tasks['custom-id-123'] to be {task}, got {runtime.tasks['custom-id-123']}"


class TestTaskRuntimeGetTasks:
    """Test TaskRuntime get_tasks method."""

    def test_get_tasks_empty(self):
        """Test getting tasks when runtime is empty."""
        runtime = TaskRuntime()
        tasks = runtime.get_tasks()
        
        assert tasks == {}, f"expect runtime.get_tasks() to be empty, got {tasks}"
        assert len(tasks) == 0, f"expect runtime.get_tasks() to have 0 tasks, got {len(tasks)}"

    def test_get_tasks_with_tasks(self):
        """Test getting tasks when runtime has tasks."""
        runtime = TaskRuntime()
        task1 = AgentTask(name="Task 1")
        task2 = AgentTask(name="Task 2")
        
        runtime.add_task(task1)
        runtime.add_task(task2)
        
        tasks = runtime.get_tasks()
        
        assert len(tasks) == 2, f"expect runtime.get_tasks() to have 2 tasks, got {len(tasks)}"
        assert task1.id in tasks, f"expect runtime.get_tasks() to contain {task1.id}, got {tasks}"
        assert task2.id in tasks, f"expect runtime.get_tasks() to contain {task2.id}, got {tasks}"

    def test_get_tasks_returns_reference(self):
        """Test that get_tasks returns a reference to the tasks dict."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        tasks = runtime.get_tasks()
        assert tasks is runtime.tasks, f"expect tasks to be {runtime.tasks}, got {tasks}"


class TestTaskRuntimeFilterTasks:
    """Test TaskRuntime filter_tasks method."""

    def test_filter_tasks_by_status(self):
        """Test filtering tasks by status."""
        runtime = TaskRuntime()
        task1 = AgentTask(name="Task 1", status=TaskStatus.PENDING)
        task2 = AgentTask(name="Task 2", status=TaskStatus.RUNNING)
        task3 = AgentTask(name="Task 3", status=TaskStatus.PENDING)
        
        runtime.add_task(task1)
        runtime.add_task(task2)
        runtime.add_task(task3)
        
        pending_tasks = runtime.filter_tasks("status", TaskStatus.PENDING)
        
        assert len(pending_tasks) == 2, f"expect runtime.filter_tasks('status', TaskStatus.PENDING) to have 2 tasks, got {len(pending_tasks)}"
        assert task1 in pending_tasks, f"expect runtime.filter_tasks('status', TaskStatus.PENDING) to contain task1, got {pending_tasks}"
        assert task3 in pending_tasks, f"expect runtime.filter_tasks('status', TaskStatus.PENDING) to contain task3, got {pending_tasks}"
        assert task2 not in pending_tasks, f"expect runtime.filter_tasks('status', TaskStatus.PENDING) not to contain task2, got {pending_tasks}"

    def test_filter_tasks_by_priority(self):
        """Test filtering tasks by priority."""
        runtime = TaskRuntime()
        task1 = AgentTask(name="Task 1", priority=TaskPriority.LOW)
        task2 = AgentTask(name="Task 2", priority=TaskPriority.HIGH)
        task3 = AgentTask(name="Task 3", priority=TaskPriority.HIGH)
        
        runtime.add_task(task1)
        runtime.add_task(task2)
        runtime.add_task(task3)
        
        high_priority_tasks = runtime.filter_tasks("priority", TaskPriority.HIGH)
        
        assert len(high_priority_tasks) == 2, f"expect runtime.filter_tasks('priority', TaskPriority.HIGH) to have 2 tasks, got {len(high_priority_tasks)}"
        assert task2 in high_priority_tasks, f"expect runtime.filter_tasks('priority', TaskPriority.HIGH) to contain task2, got {high_priority_tasks}"
        assert task3 in high_priority_tasks, f"expect runtime.filter_tasks('priority', TaskPriority.HIGH) to contain task3, got {high_priority_tasks}"

    def test_filter_tasks_by_name(self):
        """Test filtering tasks by name."""
        runtime = TaskRuntime()
        task1 = AgentTask(name="Important Task")
        task2 = AgentTask(name="Regular Task")
        task3 = AgentTask(name="Important Task")
        
        runtime.add_task(task1)
        runtime.add_task(task2)
        runtime.add_task(task3)
        
        important_tasks = runtime.filter_tasks("name", "Important Task")
        
        assert len(important_tasks) == 2, f"expect runtime.filter_tasks('name', 'Important Task') to have 2 tasks, got {len(important_tasks)}"
        assert task1 in important_tasks, f"expect runtime.filter_tasks('name', 'Important Task') to contain task1, got {important_tasks}"
        assert task3 in important_tasks, f"expect runtime.filter_tasks('name', 'Important Task') to contain task3, got {important_tasks}"

    def test_filter_tasks_no_match(self):
        """Test filtering tasks with no matches."""
        runtime = TaskRuntime()
        task = AgentTask(status=TaskStatus.PENDING)
        runtime.add_task(task)
        
        completed_tasks = runtime.filter_tasks("status", TaskStatus.COMPLETED)
        
        assert len(completed_tasks) == 0, f"expect runtime.filter_tasks('status', TaskStatus.COMPLETED) to have 0 tasks, got {len(completed_tasks)}"
        assert completed_tasks == [], f"expect [], got {completed_tasks}"

    def test_filter_tasks_empty_runtime(self):
        """Test filtering tasks on empty runtime."""
        runtime = TaskRuntime()
        filtered = runtime.filter_tasks("status", TaskStatus.PENDING)
        
        assert filtered == [], f"expect runtime.filter_tasks('status', TaskStatus.PENDING) to return [], got {filtered}"


class TestTaskRuntimeUpdateTask:
    """Test TaskRuntime update_task method."""

    def test_update_task_status(self):
        """Test updating a task's status."""
        runtime = TaskRuntime()
        task = AgentTask(status=TaskStatus.PENDING)
        runtime.add_task(task)
        
        runtime.update_task(task.id, status=TaskStatus.RUNNING)
        
        assert task.status == TaskStatus.RUNNING, f"expect after update task, task status to be {TaskStatus.RUNNING}, got {task.status}"

    def test_update_task_multiple_attributes(self):
        """Test updating multiple task attributes."""
        runtime = TaskRuntime()
        task = AgentTask(name="Old Name", priority=TaskPriority.LOW)
        runtime.add_task(task)
        
        runtime.update_task(
            task.id,
            name="New Name",
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING
        )
        
        assert task.name == "New Name", f"expect after update task, task name to be 'New Name', got {task.name}"
        assert task.priority == TaskPriority.HIGH, f"expect after update task, task priority to be {TaskPriority.HIGH}, got {task.priority}"
        assert task.status == TaskStatus.RUNNING, f"expect after update task, task status to be {TaskStatus.RUNNING}, got {task.status}"

    def test_update_task_updates_last_update(self):
        """Test that updating a task updates last_update timestamp."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        initial_update = runtime.last_update
        import time
        time.sleep(0.01)
        
        runtime.update_task(task.id, status=TaskStatus.RUNNING)
        
        assert runtime.last_update > initial_update, f"expect after update task, runtime.last_update to be greater than initial_update, got {runtime.last_update}"

    def test_update_task_not_found(self):
        """Test updating a task that doesn't exist raises error."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        with pytest.raises(ValueError, match="Task with id .* not found"):
            runtime.update_task("non-existent-id", status=TaskStatus.RUNNING)

    def test_update_task_no_tasks(self):
        """Test updating when runtime has no tasks raises error."""
        runtime = TaskRuntime()
        
        with pytest.raises(ValueError, match="No tasks available to update"):
            runtime.update_task("any-id", status=TaskStatus.RUNNING)

    def test_update_task_start_time(self):
        """Test updating task start time."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        start_time = datetime.now(UTC)
        runtime.update_task(task.id, start_time=start_time)
        
        assert task.start_time == start_time, f"expect after update task, task start_time to be {start_time}, got {task.start_time}"

    def test_update_task_end_time(self):
        """Test updating task end time."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        end_time = datetime.now(UTC)
        runtime.update_task(task.id, end_time=end_time)
        
        assert task.end_time == end_time, f"expect after update task, task end_time to be {end_time}, got {task.end_time}"


class TestTaskRuntimeClearTasks:
    """Test TaskRuntime clear_tasks method."""

    def test_clear_tasks_empty_runtime(self):
        """Test clearing tasks on empty runtime."""
        runtime = TaskRuntime()
        runtime.clear_tasks()
        
        assert len(runtime.tasks) == 0, f"expect after clear_tasks, runtime.tasks to have 0 tasks, got {len(runtime.tasks)}"
        assert runtime.status == TaskStatus.IDLE, f"expect after clear_tasks, runtime.status to be TaskStatus.IDLE, got {runtime.status}"

    def test_clear_tasks_with_tasks(self):
        """Test clearing tasks when runtime has tasks."""
        runtime = TaskRuntime()
        task1 = AgentTask()
        task2 = AgentTask()
        
        runtime.add_task(task1)
        runtime.add_task(task2)
        assert len(runtime.tasks) == 2, f"expect after add_task, runtime.tasks to have 2 tasks, got {len(runtime.tasks)}"
        
        runtime.clear_tasks()
        
        assert len(runtime.tasks) == 0, f"expect after clear_tasks, runtime.tasks to have 0 tasks, got {len(runtime.tasks)}"
        assert runtime.status == TaskStatus.IDLE, f"expect after clear_tasks, runtime.status to be TaskStatus.IDLE, got {runtime.status}"

    def test_clear_tasks_updates_status(self):
        """Test that clearing tasks sets status to IDLE."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        runtime.clear_tasks()
        
        assert runtime.status == TaskStatus.IDLE, f"expect after clear_tasks, runtime.status to be   TaskStatus.IDLE, got {runtime.status}"

    def test_clear_tasks_updates_last_update(self):
        """Test that clearing tasks updates last_update timestamp."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        initial_update = runtime.last_update
        import time
        time.sleep(0.01)
        
        runtime.clear_tasks()
        
        assert runtime.last_update > initial_update, f"expect after clear_tasks, runtime.last_update to be greater than initial_update, got {runtime.last_update}"


class TestTaskRuntimeEventLoop:
    """Test TaskRuntime event loop methods."""

    def test_init_loop(self):
        """Test initializing event loop."""
        runtime = TaskRuntime()
        runtime.init_loop()
        
        assert runtime.loop is not None, f"expect runtime.loop is not None, got {runtime.loop}"
        loop_is_event_loop = isinstance(runtime.loop, asyncio.AbstractEventLoop)
        assert loop_is_event_loop, f"expect runtime.loop to be an instance of asyncio.AbstractEventLoop, got {type(runtime.loop)}"
        
        # Cleanup
        runtime.terminate_loop()

    def test_terminate_loop(self):
        """Test terminating event loop."""
        runtime = TaskRuntime()
        runtime.init_loop()
        
        assert runtime.loop is not None, f"expect runtime.loop is not None, got {runtime.loop}"
        runtime.terminate_loop()
        
        assert runtime.loop.is_closed(), f"expect runtime.loop to be closed, got {runtime.loop.is_closed()}"

    def test_init_loop_creates_new_loop(self):
        """Test that init_loop creates a new event loop."""
        runtime = TaskRuntime()
        runtime.init_loop()
        loop1 = runtime.loop
        runtime.terminate_loop()
        
        runtime.init_loop()
        loop2 = runtime.loop
        
        assert loop1 is not loop2, f"expect loop1 is not {loop2}, got {loop1}"
        
        # Cleanup
        runtime.terminate_loop()


class TestTaskRuntimeAsyncExecution:
    """Test TaskRuntime async execution methods."""

    @pytest.mark.asyncio
    async def test_run_empty_runtime(self):
        """Test running with no tasks."""
        runtime = TaskRuntime()
        results = await runtime.run()
        
        assert results == {}, f"expect the runtime.run() result to be {{}}, got {results}"

    @pytest.mark.asyncio
    async def test_run_single_task(self):
        """Test running a single task."""
        runtime = TaskRuntime()
        
        # Create mock agent
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.data = "Success"
        
        async def mock_run(*args, **kwargs):
            return mock_result
        
        mock_agent.run = mock_run
        
        # Create and add task
        task = AgentTask(agent=mock_agent, status=TaskStatus.IDLE)
        runtime.add_task(task)
        
        # Run tasks
        results = await runtime.run()
        
        assert len(results) == 1, f"expect runtime.run() to return 1 result, got {len(results)}"
        assert task.id in results, f"expect runtime.run() result to contain task.id, got {results}"
        assert results[task.id]["status"] == TaskStatus.COMPLETED, f"expect runtime.run() result to have status {TaskStatus.COMPLETED}, got {results[task.id]['status']}"
        assert results[task.id]["result"] == mock_result, f"expect runtime.run() result to have result {mock_result}, got {results[task.id]['result']}"

    @pytest.mark.asyncio
    async def test_run_multiple_tasks(self):
        """Test running multiple tasks concurrently."""
        runtime = TaskRuntime()
        
        # Create mock agents
        mock_agent1 = MagicMock()
        mock_agent2 = MagicMock()
        mock_result1 = MagicMock()
        mock_result2 = MagicMock()
        
        async def mock_run1(*args, **kwargs):
            await asyncio.sleep(0.01)
            return mock_result1
        
        async def mock_run2(*args, **kwargs):
            await asyncio.sleep(0.01)
            return mock_result2
        
        mock_agent1.run = mock_run1
        mock_agent2.run = mock_run2
        
        # Create and add tasks
        task1 = AgentTask(agent=mock_agent1, status=TaskStatus.IDLE)
        task2 = AgentTask(agent=mock_agent2, status=TaskStatus.IDLE)
        runtime.add_task(task1)
        runtime.add_task(task2)
        
        # Run tasks
        results = await runtime.run()
        
        assert len(results) == 2, f"expect runtime.run() to return 2 results, got {len(results)}"
        assert task1.id in results, f"expect runtime.run() result to contain task1.id, got {results}"
        assert task2.id in results, f"expect runtime.run() result to contain task2.id, got {results}"
        assert results[task1.id]["status"] == TaskStatus.COMPLETED, f"expect runtime.run() result to have status {TaskStatus.COMPLETED}, got {results[task1.id]['status']}"
        assert results[task2.id]["status"] == TaskStatus.COMPLETED, f"expect runtime.run() result to have status {TaskStatus.COMPLETED}, got {results[task2.id]['status']}"

    @pytest.mark.asyncio
    async def test_run_task_with_failure(self):
        """Test running a task that fails."""
        runtime = TaskRuntime()
        
        # Create mock agent that raises exception
        mock_agent = MagicMock()
        
        async def mock_run_fail(*args, **kwargs):
            raise TaskRuntimeTestError("Task failed")
        
        mock_agent.run = mock_run_fail
        
        # Create and add task
        task = AgentTask(agent=mock_agent, status=TaskStatus.IDLE)
        runtime.add_task(task)
        
        # Run tasks - should handle exception
        with pytest.raises(ExceptionGroup) as exc_info:
            await runtime.run()
        inner_errors = exc_info.value.exceptions
        assert len(inner_errors) == 1, f"expect runtime.run failure group contains one inner error as 1, got {len(inner_errors)}"
        assert isinstance(inner_errors[0], TaskRuntimeTestError), f"expect runtime.run failure wraps TaskRuntimeTestError, got {type(inner_errors[0])}"
        assert str(inner_errors[0]) == "Task failed", f"expect runtime.run failure message is 'Task failed', got {inner_errors[0]}"

    @pytest.mark.asyncio
    async def test_get_task_status_all_tasks(self):
        """Test getting status of all tasks."""
        runtime = TaskRuntime()
        task1 = AgentTask(status=TaskStatus.PENDING)
        task2 = AgentTask(status=TaskStatus.RUNNING)
        
        runtime.add_task(task1)
        runtime.add_task(task2)
        
        statuses = await runtime.get_task_status()
        
        assert len(statuses) == 2, f"expect runtime.get_task_status() to return 2 statuses, got {len(statuses)}"
        assert task1.id in statuses, f"expect runtime.get_task_status() result to contain task1.id, got {statuses}"
        assert task2.id in statuses, f"expect runtime.get_task_status() result to contain task2.id, got {statuses}"
        assert statuses[task1.id] == TaskStatus.PENDING, f"expect runtime.get_task_status() result to have status {TaskStatus.PENDING}, got {statuses[task1.id]}"
        assert statuses[task2.id] == TaskStatus.RUNNING, f"expect runtime.get_task_status() result to have status {TaskStatus.RUNNING}, got {statuses[task2.id]}"

    @pytest.mark.asyncio
    async def test_get_task_status_specific_task(self):
        """Test getting status of a specific task."""
        runtime = TaskRuntime()
        task = AgentTask(status=TaskStatus.RUNNING)
        runtime.add_task(task)
        
        status = await runtime.get_task_status(task.id)
        
        assert status == TaskStatus.RUNNING, f"expect runtime.get_task_status(task.id) to return {TaskStatus.RUNNING}, got {status}"

    @pytest.mark.asyncio
    async def test_get_task_status_no_tasks(self):
        """Test getting status when runtime has no tasks."""
        runtime = TaskRuntime()
        
        with pytest.raises(ValueError, match="No tasks available"):
            await runtime.get_task_status()

    @pytest.mark.asyncio
    async def test_get_task_status_task_not_found(self):
        """Test getting status of non-existent task."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        with pytest.raises(ValueError, match="Task with id .* not found"):
            await runtime.get_task_status("non-existent-id")


class TestTaskRuntimeSyncExecution:
    """Test TaskRuntime synchronous execution methods."""

    def test_run_sync_empty_runtime(self):
        """Test synchronous run with no tasks."""
        runtime = TaskRuntime()
        results = runtime.run_sync()
        
        assert results == {}, f"expect runtime.run_sync() to return {{}}, got {results}"

    def test_run_sync_single_task(self):
        """Test synchronous run with a single task."""
        runtime = TaskRuntime()
        
        # Create mock agent
        mock_agent = MagicMock()
        mock_result = MagicMock()
        mock_result.data = "Success"
        
        async def mock_run(*args, **kwargs):
            return mock_result
        
        mock_agent.run = mock_run
        
        # Create and add task
        task = AgentTask(agent=mock_agent, status=TaskStatus.IDLE)
        runtime.add_task(task)
        
        # Run tasks synchronously
        results = runtime.run_sync()
        
        assert len(results) == 1, f"expect runtime.run_sync() to return 1 result, got {len(results)}"
        assert task.id in results, f"expect runtime.run_sync() result to contain task.id, got {results}"
        assert results[task.id]["status"] == TaskStatus.COMPLETED, f"expect runtime.run_sync() result to have status {TaskStatus.COMPLETED}, got {results[task.id]['status']}"

    def test_run_async_func(self):
        """Test running an async function synchronously."""
        runtime = TaskRuntime()
        
        async def sample_async_func(x, y):
            await asyncio.sleep(0.01)
            return x + y
        
        result = runtime.run_async_func(sample_async_func, 5, 10)
        
        assert result == 15, f"expect runtime.run_async_func() to return 15, got {result}"

    def test_run_async_func_with_kwargs(self):
        """Test running an async function with kwargs."""
        runtime = TaskRuntime()
        
        async def sample_async_func(x, y, multiplier=1):
            await asyncio.sleep(0.01)
            return (x + y) * multiplier
        
        result = runtime.run_async_func(sample_async_func, 5, 10, multiplier=2)
        
        assert result == 30, f"expect runtime.run_async_func() to return     30, got {result}"


class TestTaskRuntimeEdgeCases:
    """Test TaskRuntime edge cases and error handling."""

    def test_add_same_task_twice(self):
        """Test adding the same task instance twice."""
        runtime = TaskRuntime()
        task = AgentTask(id="duplicate-id")
        
        runtime.add_task(task)
        runtime.add_task(task)
        
        # Should have one task (overwritten)
        assert len(runtime.tasks) == 1, f"expect runtime.tasks to have 1 task, got {len(runtime.tasks)}"
        assert "duplicate-id" in runtime.tasks, f"expect runtime.tasks to contain 'duplicate-id', got {runtime.tasks}"

    def test_filter_tasks_invalid_attribute(self):
        """Test filtering by non-existent attribute."""
        runtime = TaskRuntime()
        task = AgentTask()
        runtime.add_task(task)
        
        with pytest.raises(AttributeError):
            runtime.filter_tasks("non_existent_attr", "value")

    def test_update_task_empty_kwargs(self):
        """Test updating task with no attributes."""
        runtime = TaskRuntime()
        task = AgentTask(status=TaskStatus.PENDING)
        runtime.add_task(task)
        
        # Should not raise error
        runtime.update_task(task.id)
        
        # Status should remain unchanged
        assert task.status == TaskStatus.PENDING, f"expect runtime.update_task() to leave status as {TaskStatus.PENDING}, got {task.status}"

    def test_runtime_state_persistence(self):
        """Test that runtime maintains state across operations."""
        runtime = TaskRuntime()
        
        # Add tasks
        task1 = AgentTask(name="Task 1")
        task2 = AgentTask(name="Task 2")
        runtime.add_task(task1)
        runtime.add_task(task2)
        
        # Update one task
        runtime.update_task(task1.id, status=TaskStatus.RUNNING)
        
        # Verify state
        assert len(runtime.tasks) == 2, f"expect runtime.tasks to have 2 tasks, got {len(runtime.tasks)}"
        assert runtime.tasks[task1.id].status == TaskStatus.RUNNING, f"expect runtime.tasks[task1.id] to have status {TaskStatus.RUNNING}, got {runtime.tasks[task1.id].status}"
        assert runtime.tasks[task2.id].status == TaskStatus.PENDING, f"expect runtime.tasks[task2.id] to have status {TaskStatus.PENDING}, got {runtime.tasks[task2.id].status}"
        
        # Filter and verify
        running_tasks = runtime.filter_tasks("status", TaskStatus.RUNNING)
        assert len(running_tasks) == 1, f"expect runtime.filter_tasks() to return 1 task, got {len(running_tasks)}"
        assert running_tasks[0] == task1, f"expect runtime.filter_tasks() to return task1, got {running_tasks[0]}"
