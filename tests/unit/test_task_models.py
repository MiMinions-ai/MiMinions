"""
Unit tests for task models.

Tests Task, TaskStatus, TaskDependency, and all validation logic.
"""

import pytest
from datetime import datetime, timedelta
from pydantic import ValidationError
import uuid

from src.miminions.task.models import Task, TaskStatus, TaskDependency, TaskPriority


class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_all_status_values(self):
        """Test all TaskStatus enum values exist."""
        assert TaskStatus.PENDING == "pending"
        assert TaskStatus.RUNNING == "running"
        assert TaskStatus.COMPLETED == "completed"
        assert TaskStatus.FAILED == "failed"
        assert TaskStatus.CANCELLED == "cancelled"

    def test_status_from_string(self):
        """Test creating TaskStatus from string."""
        assert TaskStatus("pending") == TaskStatus.PENDING
        assert TaskStatus("running") == TaskStatus.RUNNING

    def test_invalid_status(self):
        """Test invalid status raises error."""
        with pytest.raises(ValueError):
            TaskStatus("invalid_status")


class TestTaskPriority:
    """Test TaskPriority constants."""

    def test_priority_values(self):
        """Test priority constants have correct values."""
        assert TaskPriority.HIGH == 0
        assert TaskPriority.MEDIUM == 50
        assert TaskPriority.LOW == 100

    def test_priority_ordering(self):
        """Test priority values are ordered correctly (lower = higher priority)."""
        assert TaskPriority.HIGH < TaskPriority.MEDIUM
        assert TaskPriority.MEDIUM < TaskPriority.LOW


class TestTaskModel:
    """Test Task model creation and validation."""

    def test_minimal_task_creation(self):
        """Test creating task with minimal required fields."""
        now = datetime.now()
        task = Task(
            task_id="test-123",
            name="Test Task",
            created_at=now
        )

        assert task.task_id == "test-123"
        assert task.name == "Test Task"
        assert task.priority == 50  # Default
        assert task.status == TaskStatus.PENDING  # Default
        assert task.created_at == now
        assert task.input_data == {}
        assert task.retry_count == 0
        assert task.max_retries == 0

    def test_full_task_creation(self):
        """Test creating task with all fields."""
        now = datetime.now()
        task = Task(
            task_id=str(uuid.uuid4()),
            name="Complete Task",
            priority=TaskPriority.HIGH,
            status=TaskStatus.RUNNING,
            assigned_agent_id="agent-456",
            input_data={"key": "value"},
            output_data=None,
            created_at=now,
            started_at=now + timedelta(seconds=5),
            completed_at=None,
            timeout_seconds=3600,
            retry_count=2,
            max_retries=5,
            error_message=None
        )

        assert task.priority == 0
        assert task.status == TaskStatus.RUNNING
        assert task.assigned_agent_id == "agent-456"
        assert task.input_data == {"key": "value"}
        assert task.timeout_seconds == 3600
        assert task.retry_count == 2
        assert task.max_retries == 5

    def test_task_name_validation_min_length(self):
        """Test task name must be at least 1 character."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="",  # Empty name
                created_at=datetime.now()
            )
        assert "name" in str(exc_info.value)

    def test_task_name_validation_max_length(self):
        """Test task name cannot exceed 200 characters."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="x" * 201,  # Too long
                created_at=datetime.now()
            )
        assert "name" in str(exc_info.value)

    def test_priority_validation_min(self):
        """Test priority must be >= 0."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                priority=-1,  # Invalid
                created_at=datetime.now()
            )
        assert "priority" in str(exc_info.value)

    def test_priority_validation_max(self):
        """Test priority must be <= 100."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                priority=101,  # Invalid
                created_at=datetime.now()
            )
        assert "priority" in str(exc_info.value)

    def test_timeout_must_be_positive(self):
        """Test timeout_seconds must be positive."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                timeout_seconds=0,  # Invalid
                created_at=datetime.now()
            )
        assert "timeout_seconds" in str(exc_info.value)

    def test_started_at_after_created_at_validation(self):
        """Test started_at must be >= created_at."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                created_at=now,
                started_at=now - timedelta(seconds=10)  # Before created_at
            )
        assert "started_at must be >= created_at" in str(exc_info.value)

    def test_started_at_after_created_at_valid(self):
        """Test started_at can be equal to or after created_at."""
        now = datetime.now()

        # Equal
        task1 = Task(
            task_id="123",
            name="Test",
            created_at=now,
            started_at=now
        )
        assert task1.started_at == now

        # After
        task2 = Task(
            task_id="456",
            name="Test",
            created_at=now,
            started_at=now + timedelta(seconds=5)
        )
        assert task2.started_at > now

    def test_completed_at_after_started_at_validation(self):
        """Test completed_at must be >= started_at."""
        now = datetime.now()
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                created_at=now,
                started_at=now + timedelta(seconds=10),
                completed_at=now + timedelta(seconds=5)  # Before started_at
            )
        assert "completed_at must be >= started_at" in str(exc_info.value)

    def test_retry_count_within_max_validation(self):
        """Test retry_count must be <= max_retries."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                created_at=datetime.now(),
                retry_count=5,
                max_retries=3  # retry_count exceeds max
            )
        assert "retry_count must be <= max_retries" in str(exc_info.value)

    def test_retry_count_equal_to_max_valid(self):
        """Test retry_count can equal max_retries."""
        task = Task(
            task_id="123",
            name="Test",
            created_at=datetime.now(),
            retry_count=3,
            max_retries=3
        )
        assert task.retry_count == task.max_retries

    def test_assigned_agent_required_when_running(self):
        """Test assigned_agent_id required when status=running."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                status=TaskStatus.RUNNING,
                assigned_agent_id=None,  # Should be required
                created_at=datetime.now()
            )
        assert "assigned_agent_id required when status=running" in str(exc_info.value)

    def test_assigned_agent_optional_when_pending(self):
        """Test assigned_agent_id optional when status=pending."""
        task = Task(
            task_id="123",
            name="Test",
            status=TaskStatus.PENDING,
            assigned_agent_id=None,
            created_at=datetime.now()
        )
        assert task.assigned_agent_id is None

    def test_output_data_only_when_completed(self):
        """Test output_data should only be set when status=completed."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                status=TaskStatus.RUNNING,
                output_data={"result": "data"},  # Invalid for running status
                created_at=datetime.now(),
                assigned_agent_id="agent-1"
            )
        assert "output_data should only be set when status=completed" in str(exc_info.value)

    def test_output_data_valid_when_completed(self):
        """Test output_data can be set when status=completed."""
        now = datetime.now()
        task = Task(
            task_id="123",
            name="Test",
            status=TaskStatus.COMPLETED,
            output_data={"result": "success"},
            created_at=now,
            started_at=now,
            completed_at=now + timedelta(seconds=5)
        )
        assert task.output_data == {"result": "success"}

    def test_error_message_only_when_failed(self):
        """Test error_message should only be set when status=failed."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                status=TaskStatus.PENDING,
                error_message="Some error",  # Invalid for pending status
                created_at=datetime.now()
            )
        assert "error_message should only be set when status=failed" in str(exc_info.value)

    def test_error_message_valid_when_failed(self):
        """Test error_message can be set when status=failed."""
        task = Task(
            task_id="123",
            name="Test",
            status=TaskStatus.FAILED,
            error_message="Task failed due to timeout",
            created_at=datetime.now()
        )
        assert task.error_message == "Task failed due to timeout"

    def test_error_message_max_length(self):
        """Test error_message cannot exceed 2000 characters."""
        with pytest.raises(ValidationError) as exc_info:
            Task(
                task_id="123",
                name="Test",
                status=TaskStatus.FAILED,
                error_message="x" * 2001,  # Too long
                created_at=datetime.now()
            )
        assert "error_message" in str(exc_info.value)

    def test_json_encoding(self):
        """Test task can be serialized to JSON."""
        now = datetime.now()
        task = Task(
            task_id="123",
            name="Test",
            created_at=now
        )

        json_data = task.model_dump_json()
        assert "123" in json_data
        assert "Test" in json_data
        assert now.isoformat() in json_data

    def test_task_with_complex_input_data(self):
        """Test task with complex nested input data."""
        task = Task(
            task_id="123",
            name="Test",
            input_data={
                "nested": {
                    "key": "value",
                    "list": [1, 2, 3],
                    "bool": True
                }
            },
            created_at=datetime.now()
        )
        assert task.input_data["nested"]["list"] == [1, 2, 3]


class TestTaskDependency:
    """Test TaskDependency model."""

    def test_dependency_creation(self):
        """Test creating a task dependency."""
        dep = TaskDependency(
            task_id="task-b",
            depends_on_task_id="task-a"
        )
        assert dep.task_id == "task-b"
        assert dep.depends_on_task_id == "task-a"

    def test_no_self_dependency(self):
        """Test task cannot depend on itself."""
        with pytest.raises(ValidationError) as exc_info:
            TaskDependency(
                task_id="task-a",
                depends_on_task_id="task-a"  # Same as task_id
            )
        assert "Task cannot depend on itself" in str(exc_info.value)

    def test_dependency_with_uuid_ids(self):
        """Test dependency with UUID task IDs."""
        id1 = str(uuid.uuid4())
        id2 = str(uuid.uuid4())

        dep = TaskDependency(
            task_id=id1,
            depends_on_task_id=id2
        )
        assert dep.task_id == id1
        assert dep.depends_on_task_id == id2


class TestTaskEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_task_with_all_none_optional_fields(self):
        """Test task with all optional fields as None."""
        task = Task(
            task_id="123",
            name="Test",
            created_at=datetime.now()
        )
        assert task.assigned_agent_id is None
        assert task.output_data is None
        assert task.started_at is None
        assert task.completed_at is None
        assert task.timeout_seconds is None
        assert task.error_message is None

    def test_task_name_exactly_200_chars(self):
        """Test task name with exactly 200 characters (boundary)."""
        task = Task(
            task_id="123",
            name="x" * 200,
            created_at=datetime.now()
        )
        assert len(task.name) == 200

    def test_task_name_exactly_1_char(self):
        """Test task name with exactly 1 character (boundary)."""
        task = Task(
            task_id="123",
            name="x",
            created_at=datetime.now()
        )
        assert len(task.name) == 1

    def test_priority_exactly_0(self):
        """Test priority with exactly 0 (highest priority boundary)."""
        task = Task(
            task_id="123",
            name="Test",
            priority=0,
            created_at=datetime.now()
        )
        assert task.priority == 0

    def test_priority_exactly_100(self):
        """Test priority with exactly 100 (lowest priority boundary)."""
        task = Task(
            task_id="123",
            name="Test",
            priority=100,
            created_at=datetime.now()
        )
        assert task.priority == 100

    def test_retry_count_zero_with_max_retries_zero(self):
        """Test retry_count=0 and max_retries=0 (no retries)."""
        task = Task(
            task_id="123",
            name="Test",
            retry_count=0,
            max_retries=0,
            created_at=datetime.now()
        )
        assert task.retry_count == 0
        assert task.max_retries == 0

    def test_empty_input_data_dict(self):
        """Test task with empty input_data dictionary."""
        task = Task(
            task_id="123",
            name="Test",
            input_data={},
            created_at=datetime.now()
        )
        assert task.input_data == {}

    def test_timeout_exactly_1_second(self):
        """Test timeout with exactly 1 second (minimum valid)."""
        task = Task(
            task_id="123",
            name="Test",
            timeout_seconds=1,
            created_at=datetime.now()
        )
        assert task.timeout_seconds == 1

    def test_same_timestamp_for_created_started_completed(self):
        """Test task with same timestamp for created, started, and completed."""
        now = datetime.now()
        task = Task(
            task_id="123",
            name="Test",
            status=TaskStatus.COMPLETED,
            created_at=now,
            started_at=now,
            completed_at=now,
            output_data={"instant": True}
        )
        assert task.created_at == task.started_at == task.completed_at
