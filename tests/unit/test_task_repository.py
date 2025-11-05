"""
Unit tests for task repository.

Tests TaskRepository SQLite persistence, CRUD operations,
and data integrity.
"""

import pytest
from datetime import datetime, timedelta
import uuid
from pathlib import Path
import tempfile
import os

from src.miminions.task.models import Task, TaskStatus, TaskDependency, TaskPriority
from src.miminions.task.repository import TaskRepository
from src.miminions.task.exceptions import TaskNotFoundError


def create_task(name="Test", status=TaskStatus.PENDING, task_id=None):
    """Helper to create a task."""
    return Task(
        task_id=task_id or str(uuid.uuid4()),
        name=name,
        status=status,
        priority=TaskPriority.MEDIUM,
        created_at=datetime.now()
    )


class TestRepositoryInitialization:
    """Test repository initialization and schema creation."""

    def test_repository_creation_in_memory(self):
        """Test creating repository with in-memory database."""
        repo = TaskRepository(":memory:")
        assert repo.db_path == ":memory:"
        repo.close()

    def test_repository_creation_with_file(self):
        """Test creating repository with file database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"
            repo = TaskRepository(db_path)
            assert os.path.exists(db_path)
            repo.close()

    def test_repository_schema_initialized(self):
        """Test database schema is initialized."""
        repo = TaskRepository(":memory:")
        conn = repo._get_connection()
        cursor = conn.cursor()

        # Check tasks table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='tasks'")
        assert cursor.fetchone() is not None

        # Check task_dependencies table exists
        cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='task_dependencies'")
        assert cursor.fetchone() is not None

        repo.close()

    def test_repository_wal_mode_enabled(self):
        """Test WAL mode is enabled for concurrency."""
        repo = TaskRepository(":memory:")
        conn = repo._get_connection()
        cursor = conn.cursor()

        cursor.execute("PRAGMA journal_mode")
        result = cursor.fetchone()
        assert result[0].lower() == "wal"

        repo.close()

    def test_repository_indexes_created(self):
        """Test indexes are created for performance."""
        repo = TaskRepository(":memory:")
        conn = repo._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT name FROM sqlite_master WHERE type='index'")
        indexes = [row[0] for row in cursor.fetchall()]

        assert "idx_tasks_status" in indexes
        assert "idx_tasks_priority" in indexes

        repo.close()


class TestRepositorySaveTask:
    """Test saving tasks to repository."""

    def test_save_minimal_task(self):
        """Test saving task with minimal fields."""
        repo = TaskRepository(":memory:")
        task = create_task("Test Task", task_id="123")

        repo.save_task(task)

        # Verify saved
        loaded = repo.load_task("123")
        assert loaded.task_id == "123"
        assert loaded.name == "Test Task"
        repo.close()

    def test_save_complete_task(self):
        """Test saving task with all fields."""
        repo = TaskRepository(":memory:")

        now = datetime.now()
        task = Task(
            task_id="full-task",
            name="Complete Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            assigned_agent_id="agent-123",
            input_data={"key": "value", "number": 42},
            output_data=None,
            created_at=now,
            started_at=now + timedelta(seconds=1),
            completed_at=None,
            timeout_seconds=3600,
            retry_count=2,
            max_retries=5,
            error_message=None
        )

        repo.save_task(task)

        loaded = repo.load_task("full-task")
        assert loaded.name == "Complete Task"
        assert loaded.priority == 0
        assert loaded.status == TaskStatus.RUNNING
        assert loaded.assigned_agent_id == "agent-123"
        assert loaded.input_data == {"key": "value", "number": 42}
        assert loaded.timeout_seconds == 3600
        assert loaded.retry_count == 2
        assert loaded.max_retries == 5

        repo.close()

    def test_save_task_update(self):
        """Test updating existing task."""
        repo = TaskRepository(":memory:")
        task = create_task("Original", task_id="123")

        repo.save_task(task)

        # Update task
        task.name = "Updated"
        task.priority = TaskPriority.HIGH
        repo.save_task(task)

        # Verify update
        loaded = repo.load_task("123")
        assert loaded.name == "Updated"
        assert loaded.priority == 0

        repo.close()

    def test_save_task_with_complex_json(self):
        """Test saving task with complex nested JSON data."""
        repo = TaskRepository(":memory:")

        task = create_task(task_id="json-task")
        task.input_data = {
            "nested": {
                "deeply": {
                    "nested": {
                        "value": 123
                    }
                }
            },
            "list": [1, 2, 3, {"inner": "dict"}],
            "boolean": True,
            "null": None
        }

        repo.save_task(task)

        loaded = repo.load_task("json-task")
        assert loaded.input_data["nested"]["deeply"]["nested"]["value"] == 123
        assert loaded.input_data["list"][3]["inner"] == "dict"

        repo.close()

    def test_save_multiple_tasks(self):
        """Test saving multiple tasks."""
        repo = TaskRepository(":memory:")

        for i in range(10):
            task = create_task(f"Task {i}", task_id=str(i))
            repo.save_task(task)

        # Verify all saved
        for i in range(10):
            loaded = repo.load_task(str(i))
            assert loaded.name == f"Task {i}"

        repo.close()


class TestRepositoryLoadTask:
    """Test loading tasks from repository."""

    def test_load_nonexistent_task(self):
        """Test loading nonexistent task raises error."""
        repo = TaskRepository(":memory:")

        with pytest.raises(TaskNotFoundError):
            repo.load_task("nonexistent")

        repo.close()

    def test_load_task_preserves_types(self):
        """Test loading task preserves data types."""
        repo = TaskRepository(":memory:")

        now = datetime.now()
        task = Task(
            task_id="type-test",
            name="Test",
            priority=50,
            status=TaskStatus.PENDING,
            created_at=now,
            timeout_seconds=100
        )

        repo.save_task(task)
        loaded = repo.load_task("type-test")

        assert isinstance(loaded.task_id, str)
        assert isinstance(loaded.name, str)
        assert isinstance(loaded.priority, int)
        assert isinstance(loaded.status, TaskStatus)
        assert isinstance(loaded.created_at, datetime)
        assert isinstance(loaded.timeout_seconds, int)

        repo.close()

    def test_load_task_datetime_precision(self):
        """Test loading task preserves datetime precision."""
        repo = TaskRepository(":memory:")

        now = datetime.now()
        task = create_task(task_id="datetime-test")
        task.created_at = now
        task.started_at = now + timedelta(seconds=5, microseconds=123456)

        repo.save_task(task)
        loaded = repo.load_task("datetime-test")

        # SQLite timestamps might lose some microsecond precision
        assert abs((loaded.created_at - now).total_seconds()) < 0.001
        assert abs((loaded.started_at - (now + timedelta(seconds=5))).total_seconds()) < 0.1

        repo.close()


class TestRepositoryLoadAllTasks:
    """Test loading all tasks with filtering."""

    def test_load_all_tasks_empty_repository(self):
        """Test loading all tasks from empty repository."""
        repo = TaskRepository(":memory:")
        tasks = repo.load_all_tasks()
        assert tasks == []
        repo.close()

    def test_load_all_tasks(self):
        """Test loading all tasks."""
        repo = TaskRepository(":memory:")

        for i in range(5):
            task = create_task(f"Task {i}", task_id=str(i))
            repo.save_task(task)

        tasks = repo.load_all_tasks()
        assert len(tasks) == 5

        repo.close()

    def test_load_all_tasks_filtered_by_status(self):
        """Test loading tasks filtered by status."""
        repo = TaskRepository(":memory:")

        # Create tasks with different statuses
        pending = create_task("Pending", status=TaskStatus.PENDING, task_id="1")
        running = create_task("Running", status=TaskStatus.RUNNING, task_id="2")
        running.assigned_agent_id = "agent-1"
        completed = create_task("Completed", status=TaskStatus.COMPLETED, task_id="3")
        completed.output_data = {"result": "done"}

        repo.save_task(pending)
        repo.save_task(running)
        repo.save_task(completed)

        # Filter by pending
        pending_tasks = repo.load_all_tasks(status=TaskStatus.PENDING)
        assert len(pending_tasks) == 1
        assert pending_tasks[0].name == "Pending"

        # Filter by running
        running_tasks = repo.load_all_tasks(status=TaskStatus.RUNNING)
        assert len(running_tasks) == 1
        assert running_tasks[0].name == "Running"

        # Filter by completed
        completed_tasks = repo.load_all_tasks(status=TaskStatus.COMPLETED)
        assert len(completed_tasks) == 1
        assert completed_tasks[0].name == "Completed"

        repo.close()

    def test_load_all_tasks_no_filter(self):
        """Test loading all tasks without filter returns all."""
        repo = TaskRepository(":memory:")

        pending = create_task("Pending", status=TaskStatus.PENDING, task_id="1")
        running = create_task("Running", status=TaskStatus.RUNNING, task_id="2")
        running.assigned_agent_id = "agent-1"

        repo.save_task(pending)
        repo.save_task(running)

        all_tasks = repo.load_all_tasks()
        assert len(all_tasks) == 2

        repo.close()


class TestRepositoryDeleteTask:
    """Test deleting tasks."""

    def test_delete_task(self):
        """Test deleting a task."""
        repo = TaskRepository(":memory:")

        task = create_task("To Delete", task_id="delete-me")
        repo.save_task(task)

        # Verify exists
        loaded = repo.load_task("delete-me")
        assert loaded is not None

        # Delete
        repo.delete_task("delete-me")

        # Verify deleted
        with pytest.raises(TaskNotFoundError):
            repo.load_task("delete-me")

        repo.close()

    def test_delete_nonexistent_task(self):
        """Test deleting nonexistent task raises error."""
        repo = TaskRepository(":memory:")

        with pytest.raises(TaskNotFoundError):
            repo.delete_task("nonexistent")

        repo.close()

    def test_delete_task_cascades_dependencies(self):
        """Test deleting task cascades to dependencies."""
        repo = TaskRepository(":memory:")

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        repo.save_task(task_a)
        repo.save_task(task_b)

        # Create dependency
        dep = TaskDependency(task_id="b", depends_on_task_id="a")
        repo.save_dependency(dep)

        # Delete task_a
        repo.delete_task("a")

        # Dependencies should be cascade deleted
        deps = repo.load_dependencies("b")
        assert "a" not in deps

        repo.close()


class TestRepositoryDependencies:
    """Test dependency persistence."""

    def test_save_dependency(self):
        """Test saving a task dependency."""
        repo = TaskRepository(":memory:")

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        repo.save_task(task_a)
        repo.save_task(task_b)

        dep = TaskDependency(task_id="b", depends_on_task_id="a")
        repo.save_dependency(dep)

        # Verify saved
        deps = repo.load_dependencies("b")
        assert "a" in deps

        repo.close()

    def test_save_duplicate_dependency(self):
        """Test saving duplicate dependency is idempotent."""
        repo = TaskRepository(":memory:")

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        repo.save_task(task_a)
        repo.save_task(task_b)

        dep = TaskDependency(task_id="b", depends_on_task_id="a")
        repo.save_dependency(dep)
        repo.save_dependency(dep)  # Save again

        deps = repo.load_dependencies("b")
        assert len(deps) == 1  # Should only have one

        repo.close()

    def test_load_dependencies_no_dependencies(self):
        """Test loading dependencies for task with none."""
        repo = TaskRepository(":memory:")

        task = create_task("Task", task_id="123")
        repo.save_task(task)

        deps = repo.load_dependencies("123")
        assert deps == []

        repo.close()

    def test_load_dependencies_multiple(self):
        """Test loading multiple dependencies."""
        repo = TaskRepository(":memory:")

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        task_c = create_task("Task C", task_id="c")
        task_d = create_task("Task D", task_id="d")

        for task in [task_a, task_b, task_c, task_d]:
            repo.save_task(task)

        # d depends on a, b, c
        repo.save_dependency(TaskDependency(task_id="d", depends_on_task_id="a"))
        repo.save_dependency(TaskDependency(task_id="d", depends_on_task_id="b"))
        repo.save_dependency(TaskDependency(task_id="d", depends_on_task_id="c"))

        deps = repo.load_dependencies("d")
        assert len(deps) == 3
        assert set(deps) == {"a", "b", "c"}

        repo.close()

    def test_load_dependents(self):
        """Test loading tasks that depend on a given task."""
        repo = TaskRepository(":memory:")

        task_a = create_task("Task A", task_id="a")
        task_b = create_task("Task B", task_id="b")
        task_c = create_task("Task C", task_id="c")

        for task in [task_a, task_b, task_c]:
            repo.save_task(task)

        # b and c depend on a
        repo.save_dependency(TaskDependency(task_id="b", depends_on_task_id="a"))
        repo.save_dependency(TaskDependency(task_id="c", depends_on_task_id="a"))

        dependents = repo.load_dependents("a")
        assert len(dependents) == 2
        assert set(dependents) == {"b", "c"}

        repo.close()

    def test_load_dependents_no_dependents(self):
        """Test loading dependents for task with none."""
        repo = TaskRepository(":memory:")

        task = create_task("Task", task_id="123")
        repo.save_task(task)

        dependents = repo.load_dependents("123")
        assert dependents == []

        repo.close()


class TestRepositoryUpdateStatus:
    """Test updating task status."""

    def test_update_status(self):
        """Test updating task status."""
        repo = TaskRepository(":memory:")

        task = create_task("Test", task_id="123")
        repo.save_task(task)

        repo.update_status("123", TaskStatus.RUNNING, assigned_agent_id="agent-1")

        loaded = repo.load_task("123")
        assert loaded.status == TaskStatus.RUNNING
        assert loaded.assigned_agent_id == "agent-1"

        repo.close()

    def test_update_status_with_multiple_fields(self):
        """Test updating status with multiple fields."""
        repo = TaskRepository(":memory:")

        task = create_task("Test", task_id="123")
        repo.save_task(task)

        now = datetime.now()
        repo.update_status(
            "123",
            TaskStatus.COMPLETED,
            completed_at=now,
            output_data={"result": "success"}
        )

        loaded = repo.load_task("123")
        assert loaded.status == TaskStatus.COMPLETED
        assert loaded.output_data == {"result": "success"}
        assert loaded.completed_at is not None

        repo.close()

    def test_update_status_nonexistent_task(self):
        """Test updating status of nonexistent task raises error."""
        repo = TaskRepository(":memory:")

        with pytest.raises(TaskNotFoundError):
            repo.update_status("nonexistent", TaskStatus.COMPLETED)

        repo.close()


class TestRepositoryContextManager:
    """Test repository context manager."""

    def test_context_manager_enter_exit(self):
        """Test repository as context manager."""
        with TaskRepository(":memory:") as repo:
            task = create_task("Test", task_id="123")
            repo.save_task(task)
            loaded = repo.load_task("123")
            assert loaded.task_id == "123"

        # Connection should be closed after context
        # (We can't easily test this without accessing private _conn)

    def test_context_manager_with_file(self):
        """Test context manager with file database."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test.db"

            with TaskRepository(db_path) as repo:
                task = create_task("Test", task_id="123")
                repo.save_task(task)

            # Reopen and verify data persisted
            with TaskRepository(db_path) as repo:
                loaded = repo.load_task("123")
                assert loaded.task_id == "123"


class TestRepositoryEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_save_task_with_null_optional_fields(self):
        """Test saving task with all optional fields as None."""
        repo = TaskRepository(":memory:")

        task = create_task("Test", task_id="123")
        task.assigned_agent_id = None
        task.output_data = None
        task.started_at = None
        task.completed_at = None
        task.timeout_seconds = None
        task.error_message = None

        repo.save_task(task)

        loaded = repo.load_task("123")
        assert loaded.assigned_agent_id is None
        assert loaded.output_data is None
        assert loaded.started_at is None
        assert loaded.completed_at is None
        assert loaded.timeout_seconds is None
        assert loaded.error_message is None

        repo.close()

    def test_task_name_with_special_characters(self):
        """Test saving task with special characters in name."""
        repo = TaskRepository(":memory:")

        task = create_task("Task with 'quotes' and \"double quotes\" and \\ backslash", task_id="special")
        repo.save_task(task)

        loaded = repo.load_task("special")
        assert loaded.name == "Task with 'quotes' and \"double quotes\" and \\ backslash"

        repo.close()

    def test_task_name_with_unicode(self):
        """Test saving task with unicode characters."""
        repo = TaskRepository(":memory:")

        task = create_task("Task 日本語 Español 😀", task_id="unicode")
        repo.save_task(task)

        loaded = repo.load_task("unicode")
        assert loaded.name == "Task 日本語 Español 😀"

        repo.close()

    def test_very_long_error_message(self):
        """Test saving task with maximum length error message."""
        repo = TaskRepository(":memory:")

        task = create_task("Test", task_id="error-task", status=TaskStatus.FAILED)
        task.error_message = "x" * 2000  # Max length

        repo.save_task(task)

        loaded = repo.load_task("error-task")
        assert len(loaded.error_message) == 2000

        repo.close()

    def test_task_with_zero_priority(self):
        """Test saving task with priority 0."""
        repo = TaskRepository(":memory:")

        task = create_task("Test", task_id="p0")
        task.priority = 0

        repo.save_task(task)

        loaded = repo.load_task("p0")
        assert loaded.priority == 0

        repo.close()

    def test_task_with_max_priority(self):
        """Test saving task with priority 100."""
        repo = TaskRepository(":memory:")

        task = create_task("Test", task_id="p100")
        task.priority = 100

        repo.save_task(task)

        loaded = repo.load_task("p100")
        assert loaded.priority == 100

        repo.close()

    def test_concurrent_save_operations(self):
        """Test WAL mode allows concurrent operations."""
        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "concurrent.db"

            # Create two repository connections
            repo1 = TaskRepository(db_path)
            repo2 = TaskRepository(db_path)

            task1 = create_task("Task 1", task_id="1")
            task2 = create_task("Task 2", task_id="2")

            # Both should be able to save
            repo1.save_task(task1)
            repo2.save_task(task2)

            # Both should be able to read
            loaded1 = repo1.load_task("1")
            loaded2 = repo2.load_task("2")

            assert loaded1.task_id == "1"
            assert loaded2.task_id == "2"

            repo1.close()
            repo2.close()
