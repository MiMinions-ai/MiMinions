"""
Unit tests for task exceptions.

Tests all custom exception types and their attributes.
"""

import pytest

from src.miminions.task.exceptions import (
    TaskError,
    TaskNotFoundError,
    TaskQueueFullError,
    CyclicDependencyError,
    InvalidTaskStateError,
    TaskTimeoutError,
    DependencyNotMetError,
    MaxRetriesExceededError
)


class TestTaskError:
    """Test base TaskError exception."""

    def test_base_exception_inheritance(self):
        """Test TaskError inherits from Exception."""
        assert issubclass(TaskError, Exception)

    def test_raise_base_exception(self):
        """Test raising base TaskError."""
        with pytest.raises(TaskError) as exc_info:
            raise TaskError("Base error message")
        assert str(exc_info.value) == "Base error message"


class TestTaskNotFoundError:
    """Test TaskNotFoundError exception."""

    def test_inheritance(self):
        """Test TaskNotFoundError inherits from TaskError."""
        assert issubclass(TaskNotFoundError, TaskError)

    def test_exception_message(self):
        """Test exception message format."""
        error = TaskNotFoundError("task-123")
        assert str(error) == "Task not found: task-123"

    def test_exception_attributes(self):
        """Test exception stores task_id attribute."""
        error = TaskNotFoundError("task-456")
        assert error.task_id == "task-456"

    def test_raise_exception(self):
        """Test raising TaskNotFoundError."""
        with pytest.raises(TaskNotFoundError) as exc_info:
            raise TaskNotFoundError("missing-task")
        assert exc_info.value.task_id == "missing-task"
        assert "Task not found: missing-task" in str(exc_info.value)


class TestTaskQueueFullError:
    """Test TaskQueueFullError exception."""

    def test_inheritance(self):
        """Test TaskQueueFullError inherits from TaskError."""
        assert issubclass(TaskQueueFullError, TaskError)

    def test_exception_message(self):
        """Test exception message format."""
        error = TaskQueueFullError("default-queue", 1000)
        assert str(error) == "Queue 'default-queue' is full (max size: 1000)"

    def test_exception_attributes(self):
        """Test exception stores queue_name and max_size."""
        error = TaskQueueFullError("high-priority", 500)
        assert error.queue_name == "high-priority"
        assert error.max_size == 500

    def test_raise_exception(self):
        """Test raising TaskQueueFullError."""
        with pytest.raises(TaskQueueFullError) as exc_info:
            raise TaskQueueFullError("test-queue", 100)
        assert exc_info.value.queue_name == "test-queue"
        assert exc_info.value.max_size == 100


class TestCyclicDependencyError:
    """Test CyclicDependencyError exception."""

    def test_inheritance(self):
        """Test CyclicDependencyError inherits from TaskError."""
        assert issubclass(CyclicDependencyError, TaskError)

    def test_exception_message(self):
        """Test exception message format."""
        error = CyclicDependencyError("task-a", "task-b")
        assert "task-a -> task-b" in str(error)
        assert "cycle" in str(error).lower()

    def test_exception_attributes(self):
        """Test exception stores both task IDs."""
        error = CyclicDependencyError("task-x", "task-y")
        assert error.task_id == "task-x"
        assert error.depends_on_task_id == "task-y"

    def test_raise_exception(self):
        """Test raising CyclicDependencyError."""
        with pytest.raises(CyclicDependencyError) as exc_info:
            raise CyclicDependencyError("task-1", "task-2")
        assert exc_info.value.task_id == "task-1"
        assert exc_info.value.depends_on_task_id == "task-2"


class TestInvalidTaskStateError:
    """Test InvalidTaskStateError exception."""

    def test_inheritance(self):
        """Test InvalidTaskStateError inherits from TaskError."""
        assert issubclass(InvalidTaskStateError, TaskError)

    def test_exception_message(self):
        """Test exception message format."""
        error = InvalidTaskStateError("task-123", "completed", "cancel")
        expected = "Cannot cancel task task-123 with status completed"
        assert str(error) == expected

    def test_exception_attributes(self):
        """Test exception stores all attributes."""
        error = InvalidTaskStateError("task-abc", "running", "pause")
        assert error.task_id == "task-abc"
        assert error.current_status == "running"
        assert error.operation == "pause"

    def test_raise_exception(self):
        """Test raising InvalidTaskStateError."""
        with pytest.raises(InvalidTaskStateError) as exc_info:
            raise InvalidTaskStateError("task-999", "pending", "resume")
        assert exc_info.value.task_id == "task-999"
        assert exc_info.value.current_status == "pending"
        assert exc_info.value.operation == "resume"


class TestTaskTimeoutError:
    """Test TaskTimeoutError exception."""

    def test_inheritance(self):
        """Test TaskTimeoutError inherits from TaskError."""
        assert issubclass(TaskTimeoutError, TaskError)

    def test_exception_message(self):
        """Test exception message format."""
        error = TaskTimeoutError("task-123", 3600)
        expected = "Task task-123 exceeded timeout of 3600 seconds"
        assert str(error) == expected

    def test_exception_attributes(self):
        """Test exception stores task_id and timeout."""
        error = TaskTimeoutError("task-long", 7200)
        assert error.task_id == "task-long"
        assert error.timeout_seconds == 7200

    def test_raise_exception(self):
        """Test raising TaskTimeoutError."""
        with pytest.raises(TaskTimeoutError) as exc_info:
            raise TaskTimeoutError("slow-task", 60)
        assert exc_info.value.task_id == "slow-task"
        assert exc_info.value.timeout_seconds == 60


class TestDependencyNotMetError:
    """Test DependencyNotMetError exception."""

    def test_inheritance(self):
        """Test DependencyNotMetError inherits from TaskError."""
        assert issubclass(DependencyNotMetError, TaskError)

    def test_exception_message_single_dependency(self):
        """Test exception message with single unmet dependency."""
        error = DependencyNotMetError("task-b", ["task-a"])
        assert "task-b" in str(error)
        assert "task-a" in str(error)
        assert "unmet dependencies" in str(error).lower()

    def test_exception_message_multiple_dependencies(self):
        """Test exception message with multiple unmet dependencies."""
        error = DependencyNotMetError("task-d", ["task-a", "task-b", "task-c"])
        error_str = str(error)
        assert "task-d" in error_str
        assert "task-a" in error_str
        assert "task-b" in error_str
        assert "task-c" in error_str

    def test_exception_attributes(self):
        """Test exception stores task_id and unmet_dependencies list."""
        unmet = ["dep-1", "dep-2"]
        error = DependencyNotMetError("task-xyz", unmet)
        assert error.task_id == "task-xyz"
        assert error.unmet_dependencies == unmet

    def test_raise_exception(self):
        """Test raising DependencyNotMetError."""
        with pytest.raises(DependencyNotMetError) as exc_info:
            raise DependencyNotMetError("blocked-task", ["pending-1", "pending-2"])
        assert exc_info.value.task_id == "blocked-task"
        assert len(exc_info.value.unmet_dependencies) == 2


class TestMaxRetriesExceededError:
    """Test MaxRetriesExceededError exception."""

    def test_inheritance(self):
        """Test MaxRetriesExceededError inherits from TaskError."""
        assert issubclass(MaxRetriesExceededError, TaskError)

    def test_exception_message(self):
        """Test exception message format."""
        error = MaxRetriesExceededError("task-123", 3)
        expected = "Task task-123 exceeded maximum retries (3)"
        assert str(error) == expected

    def test_exception_attributes(self):
        """Test exception stores task_id and max_retries."""
        error = MaxRetriesExceededError("retry-task", 5)
        assert error.task_id == "retry-task"
        assert error.max_retries == 5

    def test_raise_exception(self):
        """Test raising MaxRetriesExceededError."""
        with pytest.raises(MaxRetriesExceededError) as exc_info:
            raise MaxRetriesExceededError("failing-task", 10)
        assert exc_info.value.task_id == "failing-task"
        assert exc_info.value.max_retries == 10


class TestExceptionCatching:
    """Test exception catching and hierarchy."""

    def test_catch_specific_exception(self):
        """Test catching specific exception type."""
        try:
            raise TaskNotFoundError("test-123")
        except TaskNotFoundError as e:
            assert e.task_id == "test-123"

    def test_catch_with_base_exception(self):
        """Test all task exceptions can be caught with TaskError."""
        exceptions_to_test = [
            TaskNotFoundError("task-1"),
            TaskQueueFullError("queue", 10),
            CyclicDependencyError("a", "b"),
            InvalidTaskStateError("task", "pending", "op"),
            TaskTimeoutError("task", 60),
            DependencyNotMetError("task", ["dep"]),
            MaxRetriesExceededError("task", 3)
        ]

        for exc in exceptions_to_test:
            try:
                raise exc
            except TaskError:
                pass  # Should catch all
            else:
                pytest.fail(f"Failed to catch {type(exc).__name__} with TaskError")

    def test_exception_type_differentiation(self):
        """Test different exception types can be distinguished."""
        try:
            raise TaskNotFoundError("task-1")
        except TaskQueueFullError:
            pytest.fail("Should not catch as TaskQueueFullError")
        except TaskNotFoundError:
            pass  # Correct

    def test_re_raise_exception(self):
        """Test exceptions can be re-raised."""
        with pytest.raises(TaskTimeoutError):
            try:
                raise TaskTimeoutError("task", 30)
            except TaskTimeoutError:
                raise  # Re-raise


class TestExceptionEdgeCases:
    """Test edge cases for exceptions."""

    def test_empty_unmet_dependencies_list(self):
        """Test DependencyNotMetError with empty list."""
        error = DependencyNotMetError("task", [])
        assert error.unmet_dependencies == []
        assert "task" in str(error)

    def test_very_long_task_id(self):
        """Test exception with very long task ID."""
        long_id = "x" * 1000
        error = TaskNotFoundError(long_id)
        assert error.task_id == long_id

    def test_zero_timeout(self):
        """Test TaskTimeoutError with zero timeout."""
        error = TaskTimeoutError("instant-task", 0)
        assert error.timeout_seconds == 0

    def test_negative_max_retries(self):
        """Test MaxRetriesExceededError with negative retries."""
        error = MaxRetriesExceededError("task", -1)
        assert error.max_retries == -1

    def test_unicode_in_error_messages(self):
        """Test exceptions with unicode characters."""
        error = TaskNotFoundError("task-™-ü-😀")
        assert "task-™-ü-😀" in str(error)

    def test_special_characters_in_queue_name(self):
        """Test TaskQueueFullError with special characters in queue name."""
        error = TaskQueueFullError("queue-[test]-(1)", 100)
        assert error.queue_name == "queue-[test]-(1)"
