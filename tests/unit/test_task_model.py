"""Unit tests for task.model module."""
import pytest
from datetime import datetime
from unittest.mock import MagicMock

from miminions.task.model import (
    TaskStatus,
    TaskPriority,
    Task,
    AgentTask,
    TaskInput,
    TaskOutput,
)


class TestTaskStatus:
    """Test TaskStatus enum."""

    def test_task_status_values(self):
        """Test all TaskStatus enum values exist."""
        assert TaskStatus.PENDING.value == "pending"
        assert TaskStatus.INITIALIZED.value == "initialized"
        assert TaskStatus.IDLE.value == "idle"
        assert TaskStatus.RUNNING.value == "running"
        assert TaskStatus.IN_PROGRESS.value == "in_progress"
        assert TaskStatus.PAUSED.value == "paused"
        assert TaskStatus.COMPLETED.value == "completed"
        assert TaskStatus.FAILED.value == "failed"
        assert TaskStatus.CANCELLED.value == "cancelled"

    def test_task_status_count(self):
        """Test total number of status values."""
        assert len(TaskStatus) == 9

    def test_task_status_comparison(self):
        """Test TaskStatus enum comparison."""
        assert TaskStatus.PENDING == TaskStatus.PENDING
        assert TaskStatus.PENDING != TaskStatus.RUNNING
        assert TaskStatus.COMPLETED != TaskStatus.FAILED

    def test_task_status_membership(self):
        """Test TaskStatus membership."""
        assert TaskStatus.RUNNING in TaskStatus
        # Enum values (not strings) are members
        assert all(status in TaskStatus for status in TaskStatus)

    def test_task_status_iteration(self):
        """Test iterating through TaskStatus."""
        statuses = list(TaskStatus)
        assert len(statuses) == 9
        assert TaskStatus.PENDING in statuses
        assert TaskStatus.COMPLETED in statuses


class TestTaskPriority:
    """Test TaskPriority enum."""

    def test_task_priority_values(self):
        """Test all TaskPriority enum values exist."""
        assert TaskPriority.LOW.value == "low"
        assert TaskPriority.MEDIUM.value == "medium"
        assert TaskPriority.HIGH.value == "high"
        assert TaskPriority.CRITICAL.value == "critical"

    def test_task_priority_count(self):
        """Test total number of priority values."""
        assert len(TaskPriority) == 4

    def test_task_priority_comparison(self):
        """Test TaskPriority enum comparison."""
        assert TaskPriority.LOW == TaskPriority.LOW
        assert TaskPriority.HIGH != TaskPriority.LOW
        assert TaskPriority.CRITICAL != TaskPriority.MEDIUM

    def test_task_priority_iteration(self):
        """Test iterating through TaskPriority."""
        priorities = list(TaskPriority)
        assert len(priorities) == 4
        assert TaskPriority.LOW in priorities
        assert TaskPriority.CRITICAL in priorities


class TestTask:
    """Test Task dataclass."""

    def test_task_creation_with_defaults(self):
        """Test creating a Task with default values."""
        task = Task()
        
        assert task.id is not None
        assert isinstance(task.id, str)
        assert len(task.id) > 0
        
        assert task.name is not None
        assert isinstance(task.name, str)
        
        assert task.description is not None
        assert isinstance(task.description, str)
        
        assert task.status == TaskStatus.PENDING
        assert task.priority == TaskPriority.MEDIUM
        assert task.start_time is None
        assert task.end_time is None

    def test_task_creation_with_custom_values(self):
        """Test creating a Task with custom values."""
        custom_id = "test-123"
        custom_name = "Test Task"
        custom_description = "A test task description"
        custom_status = TaskStatus.RUNNING
        custom_priority = TaskPriority.HIGH
        start_time = datetime.now()
        
        task = Task(
            id=custom_id,
            name=custom_name,
            description=custom_description,
            status=custom_status,
            priority=custom_priority,
            start_time=start_time
        )
        
        assert task.id == custom_id
        assert task.name == custom_name
        assert task.description == custom_description
        assert task.status == custom_status
        assert task.priority == custom_priority
        assert task.start_time == start_time
        assert task.end_time is None

    def test_task_unique_ids(self):
        """Test that each Task gets a unique ID."""
        task1 = Task()
        task2 = Task()
        
        assert task1.id != task2.id

    def test_task_status_update(self):
        """Test updating task status."""
        task = Task()
        assert task.status == TaskStatus.PENDING
        
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING
        
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED

    def test_task_priority_update(self):
        """Test updating task priority."""
        task = Task()
        assert task.priority == TaskPriority.MEDIUM
        
        task.priority = TaskPriority.HIGH
        assert task.priority == TaskPriority.HIGH
        
        task.priority = TaskPriority.CRITICAL
        assert task.priority == TaskPriority.CRITICAL

    def test_task_time_tracking(self):
        """Test task time tracking fields."""
        task = Task()
        assert task.start_time is None
        assert task.end_time is None
        
        start = datetime.now()
        task.start_time = start
        assert task.start_time == start
        
        end = datetime.now()
        task.end_time = end
        assert task.end_time == end
        assert task.end_time >= task.start_time

    def test_task_field_metadata(self):
        """Test that field metadata is properly defined."""
        from dataclasses import fields
        
        task_fields = {f.name: f for f in fields(Task)}
        
        assert "id" in task_fields
        assert "description" in task_fields["id"].metadata
        
        assert "name" in task_fields
        assert "description" in task_fields["name"].metadata
        
        assert "status" in task_fields
        assert "description" in task_fields["status"].metadata


class TestAgentTask:
    """Test AgentTask dataclass."""

    def test_agent_task_creation_with_defaults(self):
        """Test creating an AgentTask with default values."""
        agent_task = AgentTask()
        
        # Inherited Task fields
        assert agent_task.id is not None
        assert agent_task.name is not None
        assert agent_task.description is not None
        assert agent_task.status == TaskStatus.PENDING
        assert agent_task.priority == TaskPriority.MEDIUM
        
        # AgentTask specific fields
        assert agent_task.agent is None
        assert agent_task.args == []
        assert agent_task.max_turns == 5
        assert agent_task.kwargs == {}
        assert agent_task.call_back is None
        assert agent_task.result is None

    def test_agent_task_with_custom_values(self):
        """Test creating an AgentTask with custom values."""
        mock_agent = MagicMock()
        mock_callback = MagicMock()
        mock_result = MagicMock()
        
        agent_task = AgentTask(
            name="Agent Task",
            description="Test agent task",
            agent=mock_agent,
            args=["arg1", "arg2"],
            max_turns=10,
            kwargs={"key": "value"},
            call_back=mock_callback,
            result=mock_result
        )
        
        assert agent_task.name == "Agent Task"
        assert agent_task.description == "Test agent task"
        assert agent_task.agent == mock_agent
        assert agent_task.args == ["arg1", "arg2"]
        assert agent_task.max_turns == 10
        assert agent_task.kwargs == {"key": "value"}
        assert agent_task.call_back == mock_callback
        assert agent_task.result == mock_result

    def test_agent_task_inheritance(self):
        """Test that AgentTask inherits from Task."""
        agent_task = AgentTask()
        assert isinstance(agent_task, Task)
        assert isinstance(agent_task, AgentTask)

    def test_agent_task_args_list(self):
        """Test AgentTask args list manipulation."""
        agent_task = AgentTask()
        assert agent_task.args == []
        
        agent_task.args.append("arg1")
        assert len(agent_task.args) == 1
        assert agent_task.args[0] == "arg1"
        
        agent_task.args.extend(["arg2", "arg3"])
        assert len(agent_task.args) == 3

    def test_agent_task_kwargs_dict(self):
        """Test AgentTask kwargs dict manipulation."""
        agent_task = AgentTask()
        assert agent_task.kwargs == {}
        
        agent_task.kwargs["key1"] = "value1"
        assert agent_task.kwargs["key1"] == "value1"
        
        agent_task.kwargs.update({"key2": "value2", "key3": "value3"})
        assert len(agent_task.kwargs) == 3

    def test_agent_task_max_turns(self):
        """Test AgentTask max_turns configuration."""
        agent_task = AgentTask(max_turns=15)
        assert agent_task.max_turns == 15
        
        agent_task.max_turns = 20
        assert agent_task.max_turns == 20

    def test_agent_task_callback_invocation(self):
        """Test AgentTask callback can be invoked."""
        mock_callback = MagicMock()
        agent_task = AgentTask(call_back=mock_callback)
        
        # Simulate callback invocation
        if agent_task.call_back:
            agent_task.call_back(agent_task)
        
        mock_callback.assert_called_once_with(agent_task)

    def test_agent_task_result_assignment(self):
        """Test AgentTask result assignment."""
        agent_task = AgentTask()
        assert agent_task.result is None
        
        mock_result = MagicMock()
        mock_result.data = "Success"
        agent_task.result = mock_result
        
        assert agent_task.result == mock_result
        assert agent_task.result.data == "Success"


class TestTaskInput:
    """Test TaskInput dataclass."""

    def test_task_input_creation_with_defaults(self):
        """Test creating a TaskInput with default values."""
        task_input = TaskInput()
        assert task_input.params == {}

    def test_task_input_with_custom_params(self):
        """Test creating a TaskInput with custom parameters."""
        params = {"param1": "value1", "param2": 123, "param3": [1, 2, 3]}
        task_input = TaskInput(params=params)
        
        assert task_input.params == params
        assert task_input.params["param1"] == "value1"
        assert task_input.params["param2"] == 123
        assert task_input.params["param3"] == [1, 2, 3]

    def test_task_input_params_mutation(self):
        """Test TaskInput params dictionary can be mutated."""
        task_input = TaskInput()
        
        task_input.params["new_param"] = "new_value"
        assert task_input.params["new_param"] == "new_value"
        
        task_input.params.update({"another": "value"})
        assert len(task_input.params) == 2

    def test_task_input_empty_params(self):
        """Test TaskInput with explicitly empty params."""
        task_input = TaskInput(params={})
        assert task_input.params == {}
        assert len(task_input.params) == 0


class TestTaskOutput:
    """Test TaskOutput dataclass."""

    def test_task_output_creation_with_defaults(self):
        """Test creating a TaskOutput with default values."""
        task_output = TaskOutput()
        assert task_output.results == {}

    def test_task_output_with_custom_results(self):
        """Test creating a TaskOutput with custom results."""
        results = {"result1": "value1", "result2": 456, "result3": {"nested": "data"}}
        task_output = TaskOutput(results=results)
        
        assert task_output.results == results
        assert task_output.results["result1"] == "value1"
        assert task_output.results["result2"] == 456
        assert task_output.results["result3"]["nested"] == "data"

    def test_task_output_results_mutation(self):
        """Test TaskOutput results dictionary can be mutated."""
        task_output = TaskOutput()
        
        task_output.results["new_result"] = "new_value"
        assert task_output.results["new_result"] == "new_value"
        
        task_output.results.update({"another": "result"})
        assert len(task_output.results) == 2

    def test_task_output_empty_results(self):
        """Test TaskOutput with explicitly empty results."""
        task_output = TaskOutput(results={})
        assert task_output.results == {}
        assert len(task_output.results) == 0


class TestTaskDataclassIntegration:
    """Test integration between Task-related dataclasses."""

    def test_task_input_output_workflow(self):
        """Test using TaskInput and TaskOutput together."""
        # Create input
        task_input = TaskInput(params={"x": 10, "y": 20})
        
        # Simulate processing
        result_value = task_input.params["x"] + task_input.params["y"]
        
        # Create output
        task_output = TaskOutput(results={"sum": result_value})
        
        assert task_output.results["sum"] == 30

    def test_agent_task_with_input_output(self):
        """Test AgentTask with TaskInput and TaskOutput."""
        task_input = TaskInput(params={"query": "test query"})
        agent_task = AgentTask(
            name="Query Task",
            args=[task_input.params["query"]]
        )
        
        assert agent_task.args[0] == "test query"
        
        # Simulate result
        task_output = TaskOutput(results={"response": "test response"})
        mock_result = MagicMock()
        mock_result.data = task_output.results
        agent_task.result = mock_result
        
        assert agent_task.result.data == task_output.results

    def test_multiple_tasks_with_different_states(self):
        """Test creating multiple tasks with different states."""
        task1 = Task(name="Task 1", status=TaskStatus.PENDING)
        task2 = Task(name="Task 2", status=TaskStatus.RUNNING)
        task3 = Task(name="Task 3", status=TaskStatus.COMPLETED)
        
        tasks = [task1, task2, task3]
        
        assert len(tasks) == 3
        assert tasks[0].status == TaskStatus.PENDING
        assert tasks[1].status == TaskStatus.RUNNING
        assert tasks[2].status == TaskStatus.COMPLETED

    def test_task_lifecycle_simulation(self):
        """Test simulating a complete task lifecycle."""
        task = Task(name="Lifecycle Task")
        
        # Initial state
        assert task.status == TaskStatus.PENDING
        assert task.start_time is None
        assert task.end_time is None
        
        # Start task
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        assert task.status == TaskStatus.RUNNING
        assert task.start_time is not None
        
        # Complete task
        task.status = TaskStatus.COMPLETED
        task.end_time = datetime.now()
        assert task.status == TaskStatus.COMPLETED
        assert task.end_time is not None
        assert task.end_time >= task.start_time
