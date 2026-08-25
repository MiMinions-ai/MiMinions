"""Unit tests for task.model module."""
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
        assert TaskStatus.PENDING.value == "pending", f"expect 'pending', got {TaskStatus.PENDING.value}"
        assert TaskStatus.INITIALIZED.value == "initialized", f"expect 'initialized', got {TaskStatus.INITIALIZED.value}"
        assert TaskStatus.IDLE.value == "idle", f"expect 'idle', got {TaskStatus.IDLE.value}"
        assert TaskStatus.RUNNING.value == "running", f"expect 'running', got {TaskStatus.RUNNING.value}"
        assert TaskStatus.IN_PROGRESS.value == "in_progress", f"expect 'in_progress', got {TaskStatus.IN_PROGRESS.value}"
        assert TaskStatus.PAUSED.value == "paused", f"expect 'paused', got {TaskStatus.PAUSED.value}"
        assert TaskStatus.COMPLETED.value == "completed", f"expect 'completed', got {TaskStatus.COMPLETED.value}"
        assert TaskStatus.FAILED.value == "failed", f"expect 'failed', got {TaskStatus.FAILED.value}"
        assert TaskStatus.CANCELLED.value == "cancelled", f"expect 'cancelled', got {TaskStatus.CANCELLED.value}"

    def test_task_status_count(self):
        """Test total number of status values."""
        assert len(TaskStatus) == 9, f"expect 9, got {len(TaskStatus)}"

    def test_task_status_comparison(self):
        """Test TaskStatus enum comparison."""
        assert TaskStatus.PENDING == TaskStatus.PENDING, f"expect TaskStatus.PENDING, got {TaskStatus.PENDING}"
        assert TaskStatus.PENDING != TaskStatus.RUNNING, f"expect value != TaskStatus.RUNNING, got {TaskStatus.PENDING}"
        assert TaskStatus.COMPLETED != TaskStatus.FAILED, f"expect value != TaskStatus.FAILED, got {TaskStatus.COMPLETED}"

    def test_task_status_membership(self):
        """Test TaskStatus membership."""
        assert TaskStatus.RUNNING in TaskStatus, f"expect contains TaskStatus.RUNNING, got {TaskStatus}"
        # Enum values (not strings) are members
        assert all(status in TaskStatus for status in TaskStatus), f"expect all items matching status in TaskStatus, got {[' ', '+', ' ', 'i', 't', 'e', 'r', 'a', 'b', 'l', 'e', ' ', '+', ' ']}"

    def test_task_status_iteration(self):
        """Test iterating through TaskStatus."""
        statuses = list(TaskStatus)
        assert len(statuses) == 9, f"expect 9, got {len(statuses)}"
        assert TaskStatus.PENDING in statuses, f"expect contains TaskStatus.PENDING, got {statuses}"
        assert TaskStatus.COMPLETED in statuses, f"expect contains TaskStatus.COMPLETED, got {statuses}"


class TestTaskPriority:
    """Test TaskPriority enum."""

    def test_task_priority_values(self):
        """Test all TaskPriority enum values exist."""
        assert TaskPriority.LOW.value == "low", f"expect 'low', got {TaskPriority.LOW.value}"
        assert TaskPriority.MEDIUM.value == "medium", f"expect 'medium', got {TaskPriority.MEDIUM.value}"
        assert TaskPriority.HIGH.value == "high", f"expect 'high', got {TaskPriority.HIGH.value}"
        assert TaskPriority.CRITICAL.value == "critical", f"expect 'critical', got {TaskPriority.CRITICAL.value}"

    def test_task_priority_count(self):
        """Test total number of priority values."""
        assert len(TaskPriority) == 4, f"expect 4, got {len(TaskPriority)}"

    def test_task_priority_comparison(self):
        """Test TaskPriority enum comparison."""
        assert TaskPriority.LOW == TaskPriority.LOW, f"expect TaskPriority.LOW, got {TaskPriority.LOW}"
        assert TaskPriority.HIGH != TaskPriority.LOW, f"expect value != TaskPriority.LOW, got {TaskPriority.HIGH}"
        assert TaskPriority.CRITICAL != TaskPriority.MEDIUM, f"expect value != TaskPriority.MEDIUM, got {TaskPriority.CRITICAL}"

    def test_task_priority_iteration(self):
        """Test iterating through TaskPriority."""
        priorities = list(TaskPriority)
        assert len(priorities) == 4, f"expect 4, got {len(priorities)}"
        assert TaskPriority.LOW in priorities, f"expect contains TaskPriority.LOW, got {priorities}"
        assert TaskPriority.CRITICAL in priorities, f"expect contains TaskPriority.CRITICAL, got {priorities}"


class TestTask:
    """Test Task dataclass."""

    def test_task_creation_with_defaults(self):
        """Test creating a Task with default values."""
        task = Task()
        
        assert task.id is not None, f"expect task.id is initialized and is not None, got {task.id}"
        assert isinstance(task.id, str), f"expect task.id to be a str, got {type(task.id)}"
        assert len(task.id) > 0, f"expect the length of task.id > 0, got {len(task.id)}"
        
        assert task.name is not None, f"expect task.name is not None, got {task.name}"
        assert isinstance(task.name, str), f"expect task.name to be a str, got {type(task.name)}"
        
        assert task.description is not None, f"expect task.description is not None, got {task.description}"
        assert isinstance(task.description, str), f"expect task.description to be a str, got {type(task.description)}"
        
        assert task.status == TaskStatus.PENDING, f"expect the task.status to be {TaskStatus.PENDING}, got {task.status}"
        assert task.priority == TaskPriority.MEDIUM, f"expect the task.priority to be {TaskPriority.MEDIUM}, got {task.priority}"
        assert task.start_time is None, f"expect the task.start_time to be {None}, got {task.start_time}"
        assert task.end_time is None, f"expect the task.end_time to be {None}, got {task.end_time}"

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
        
        assert task.id == custom_id, f"expect the task.id to be {custom_id}, got {task.id}"
        assert task.name == custom_name, f"expect the task.name to be {custom_name}, got {task.name}"
        assert task.description == custom_description, f"expect the task.description to be {custom_description}, got {task.description}"
        assert task.status == custom_status, f"expect the task.status to be {custom_status}, got {task.status}"
        assert task.priority == custom_priority, f"expect the task.priority to be {custom_priority}, got {task.priority}"
        assert task.start_time == start_time, f"expect the task.start_time to be {start_time}, got {task.start_time}"
        assert task.end_time is None, f"expect the task.end_time to be {None}, got {task.end_time}"

    def test_task_unique_ids(self):
        """Test that each Task gets a unique ID."""
        task1 = Task()
        task2 = Task()
        
        assert task1.id != task2.id, f"expect the task1.id to be different from {task2.id}, got {task1.id}"

    def test_task_status_update(self):
        """Test updating task status."""
        task = Task()
        assert task.status == TaskStatus.PENDING, f"expect the task.status to be {TaskStatus.PENDING}, got {task.status}"
        
        task.status = TaskStatus.RUNNING
        assert task.status == TaskStatus.RUNNING, f"expect the task.status to be {TaskStatus.RUNNING}, got {task.status}"
        
        task.status = TaskStatus.COMPLETED
        assert task.status == TaskStatus.COMPLETED, f"expect the task.status to be {TaskStatus.COMPLETED}, got {task.status}"

    def test_task_priority_update(self):
        """Test updating task priority."""
        task = Task()
        assert task.priority == TaskPriority.MEDIUM, f"expect the task.priority to be {TaskPriority.MEDIUM}, got {task.priority}"
        
        task.priority = TaskPriority.HIGH
        assert task.priority == TaskPriority.HIGH, f"expect the task.priority to be {TaskPriority.HIGH}, got {task.priority}"
        
        task.priority = TaskPriority.CRITICAL
        assert task.priority == TaskPriority.CRITICAL, f"expect the task.priority to be {TaskPriority.CRITICAL}, got {task.priority}"

    def test_task_time_tracking(self):
        """Test task time tracking fields."""
        task = Task()
        assert task.start_time is None, f"expect the task.start_time to be {None}, got {task.start_time}"
        assert task.end_time is None, f"expect the task.end_time to be {None}, got {task.end_time}"
        
        start = datetime.now()
        task.start_time = start
        assert task.start_time == start, f"expect the task.start_time to be {start}, got {task.start_time}"
        
        end = datetime.now()
        task.end_time = end
        assert task.end_time == end, f"expect the task.end_time to be {end}, got {task.end_time}"
        assert task.end_time >= task.start_time, f"expect the task.end_time to be >= {task.start_time}, got {task.end_time}"

    def test_task_field_metadata(self):
        """Test that field metadata is properly defined."""
        from dataclasses import fields
        
        task_fields = {f.name: f for f in fields(Task)}
        
        assert "id" in task_fields, f"expect task_fields to contain 'id', got {task_fields}"
        assert "description" in task_fields["id"].metadata, f"expect task_fields['id'].metadata to contain 'description', got {task_fields['id'].metadata}"
        
        assert "name" in task_fields, f"expect task_fields to contain 'name', got {task_fields}"
        assert "description" in task_fields["name"].metadata, f"expect task_fields['name'].metadata to contain 'description', got {task_fields['name'].metadata}"
        
        assert "status" in task_fields, f"expect task_fields to contain 'status', got {task_fields}"
        assert "description" in task_fields["status"].metadata, f"expect task_fields['status'].metadata to contain 'description', got {task_fields['status'].metadata}"


class TestAgentTask:
    """Test AgentTask dataclass."""

    def test_agent_task_creation_with_defaults(self):
        """Test creating an AgentTask with default values."""
        agent_task = AgentTask()
        
        # Inherited Task fields
        assert agent_task.id is not None, f"expect the agent_task.id to be not None, got {agent_task.id}"
        assert agent_task.name is not None, f"expect the agent_task.name to be not None, got {agent_task.name}"
        assert agent_task.description is not None, f"expect the agent_task.description to be not None, got {agent_task.description}"
        assert agent_task.status == TaskStatus.PENDING, f"expect the agent_task.status to be {TaskStatus.PENDING}, got {agent_task.status}"
        assert agent_task.priority == TaskPriority.MEDIUM, f"expect the agent_task.priority to be {TaskPriority.MEDIUM}, got {agent_task.priority}"
        
        # AgentTask specific fields
        assert agent_task.agent is None, f"expect the agent_task.agent to be None, got {agent_task.agent}"
        assert agent_task.args == [], f"expect the agent_task.args to be [], got {agent_task.args}"
        assert agent_task.max_turns == 5, f"expect the agent_task.max_turns to be 5, got {agent_task.max_turns}"
        assert agent_task.kwargs == {}, f"expect the agent_task.kwargs to be {{}}, got {agent_task.kwargs}"
        assert agent_task.call_back is None, f"expect the agent_task.call_back to be None, got {agent_task.call_back}"
        assert agent_task.result is None, f"expect the agent_task.result to be None, got {agent_task.result}"

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
        
        assert agent_task.name == "Agent Task", f"expect the agent_task.name to be 'Agent Task', got {agent_task.name}"
        assert agent_task.description == "Test agent task", f"expect the agent_task.description to be 'Test agent task', got {agent_task.description}"
        assert agent_task.agent == mock_agent, f"expect the agent_task.agent to be mock_agent, got {agent_task.agent}"
        assert agent_task.args == ["arg1", "arg2"], f"expect the agent_task.args to be {['arg1', 'arg2']}, got {agent_task.args}"
        assert agent_task.max_turns == 10, f"expect the agent_task.max_turns to be 10, got {agent_task.max_turns}"
        assert agent_task.kwargs == {"key": "value"}, f"expect the agent_task.kwargs to be {{'key': 'value'}}, got {agent_task.kwargs}"
        assert agent_task.call_back == mock_callback, f"expect the agent_task.call_back to be {mock_callback}, got {agent_task.call_back}"
        assert agent_task.result == mock_result, f"expect the agent_task.result to be {mock_result}, got {agent_task.result}"

    def test_agent_task_inheritance(self):
        """Test that AgentTask inherits from Task."""
        agent_task = AgentTask()
        assert isinstance(agent_task, Task), f"expect the agent_task to be an instance of Task, got {type(agent_task)}"
        assert isinstance(agent_task, AgentTask), f"expect the agent_task to be an instance of AgentTask, got {type(agent_task)}"

    def test_agent_task_args_list(self):
        """Test AgentTask args list manipulation."""
        agent_task = AgentTask()
        assert agent_task.args == [], f"expect the agent_task.args to be [], got {agent_task.args}"
        
        agent_task.args.append("arg1")
        assert len(agent_task.args) == 1, f"expect the agent_task.args length to be 1, got {len(agent_task.args)}"
        assert agent_task.args[0] == "arg1", f"expect the agent_task.args[0] to be 'arg1', got {agent_task.args[0]}"
        
        agent_task.args.extend(["arg2", "arg3"])
        assert len(agent_task.args) == 3, f"expect the agent_task.args length to be 3, got {len(agent_task.args)}"

    def test_agent_task_kwargs_dict(self):
        """Test AgentTask kwargs dict manipulation."""
        agent_task = AgentTask()
        assert agent_task.kwargs == {}, f"expect the agent_task.kwargs to be {{}}, got {agent_task.kwargs}"
        
        agent_task.kwargs["key1"] = "value1"
        assert agent_task.kwargs["key1"] == "value1", f"expect the agent_task.kwargs['key1'] to be 'value1', got {agent_task.kwargs['key1']}"
        
        agent_task.kwargs.update({"key2": "value2", "key3": "value3"})
        assert len(agent_task.kwargs) == 3, f"expect the agent_task.kwargs length to be 3, got {len(agent_task.kwargs)}"

    def test_agent_task_max_turns(self):
        """Test AgentTask max_turns configuration."""
        agent_task = AgentTask(max_turns=15)
        assert agent_task.max_turns == 15, f"expect the agent_task.max_turns to be 15, got {agent_task.max_turns}"
        
        agent_task.max_turns = 20
        assert agent_task.max_turns == 20, f"expect the agent_task.max_turns to be 20, got {agent_task.max_turns}"

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
        assert agent_task.result is None, f"expect the agent_task.result to be None, got {agent_task.result}"
        
        mock_result = MagicMock()
        mock_result.data = "Success"
        agent_task.result = mock_result
        
        assert agent_task.result == mock_result, f"expect the agent_task.result to be mock_result, got {agent_task.result}"
        assert agent_task.result.data == "Success", f"expect the agent_task.result.data to be 'Success', got {agent_task.result.data}"


class TestTaskInput:
    """Test TaskInput dataclass."""

    def test_task_input_creation_with_defaults(self):
        """Test creating a TaskInput with default values."""
        task_input = TaskInput()
        assert task_input.params == {}, f"expect the task_input.params to be {{}}, got {task_input.params}"

    def test_task_input_with_custom_params(self):
        """Test creating a TaskInput with custom parameters."""
        params = {"param1": "value1", "param2": 123, "param3": [1, 2, 3]}
        task_input = TaskInput(params=params)
        
        assert task_input.params == params, f"expect the task_input.params to be {params}, got {task_input.params}"
        assert task_input.params["param1"] == "value1", f"expect the task_input.params['param1'] to be 'value1', got {task_input.params['param1']}"
        assert task_input.params["param2"] == 123, f"expect the task_input.params['param2'] to be 123, got {task_input.params['param2']}"
        assert task_input.params["param3"] == [1, 2, 3], f"expect the task_input.params['param3'] to be {[1, 2, 3]}, got {task_input.params['param3']}"

    def test_task_input_params_mutation(self):
        """Test TaskInput params dictionary can be mutated."""
        task_input = TaskInput()
        
        task_input.params["new_param"] = "new_value"
        assert task_input.params["new_param"] == "new_value", f"expect the task_input.params['new_param'] to be 'new_value', got {task_input.params['new_param']}"
        
        task_input.params.update({"another": "value"})
        assert len(task_input.params) == 2, f"expect the length of task_input.params to be 2, got {len(task_input.params)}"

    def test_task_input_empty_params(self):
        """Test TaskInput with explicitly empty params."""
        task_input = TaskInput(params={})
        assert task_input.params == {}, f"expect the task_input.params to be {{}}, got {task_input.params}"
        assert len(task_input.params) == 0, f"expect the length of task_input.params to be 0, got {len(task_input.params)}"


class TestTaskOutput:
    """Test TaskOutput dataclass."""

    def test_task_output_creation_with_defaults(self):
        """Test creating a TaskOutput with default values."""
        task_output = TaskOutput()
        assert task_output.results == {}, f"expect the task_output.results to be {{}}, got {task_output.results}"

    def test_task_output_with_custom_results(self):
        """Test creating a TaskOutput with custom results."""
        results = {"result1": "value1", "result2": 456, "result3": {"nested": "data"}}
        task_output = TaskOutput(results=results)
        
        assert task_output.results == results, f"expect the task_output.results to be {results}, got {task_output.results}"
        assert task_output.results["result1"] == "value1", f"expect the task_output.results['result1'] to be 'value1', got {task_output.results['result1']}"
        assert task_output.results["result2"] == 456, f"expect the task_output.results['result2'] to be 456, got {task_output.results['result2']}"
        assert task_output.results["result3"]["nested"] == "data", f"expect the task_output.results['result3']['nested'] to be 'data', got {task_output.results['result3']['nested']}"

    def test_task_output_results_mutation(self):
        """Test TaskOutput results dictionary can be mutated."""
        task_output = TaskOutput()
        
        task_output.results["new_result"] = "new_value"
        assert task_output.results["new_result"] == "new_value", f"expect the task_output.results['new_result'] to be 'new_value', got {task_output.results['new_result']}"
        
        task_output.results.update({"another": "result"})
        assert len(task_output.results) == 2, f"expect the length of task_output.results to be 2, got {len(task_output.results)}"

    def test_task_output_empty_results(self):
        """Test TaskOutput with explicitly empty results."""
        task_output = TaskOutput(results={})
        assert task_output.results == {}, f"expect the task_output.results to be {{}}, got {task_output.results}"
        assert len(task_output.results) == 0, f"expect the length of task_output.results to be 0, got {len(task_output.results)}"


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
        
        assert task_output.results["sum"] == 30, f"expect 30, got {task_output.results['sum']}"

    def test_agent_task_with_input_output(self):
        """Test AgentTask with TaskInput and TaskOutput."""
        task_input = TaskInput(params={"query": "test query"})
        agent_task = AgentTask(
            name="Query Task",
            args=[task_input.params["query"]]
        )
        
        assert agent_task.args[0] == "test query", f"expect the agent_task.args[0] to be 'test query', got {agent_task.args[0]}"
        
        # Simulate result
        task_output = TaskOutput(results={"response": "test response"})
        mock_result = MagicMock()
        mock_result.data = task_output.results
        agent_task.result = mock_result
        
        assert agent_task.result.data == task_output.results, f"expect the agent_task.result.data to be the {task_output.results}, got {agent_task.result.data}"

    def test_multiple_tasks_with_different_states(self):
        """Test creating multiple tasks with different states."""
        task1 = Task(name="Task 1", status=TaskStatus.PENDING)
        task2 = Task(name="Task 2", status=TaskStatus.RUNNING)
        task3 = Task(name="Task 3", status=TaskStatus.COMPLETED)
        
        tasks = [task1, task2, task3]
        
        assert len(tasks) == 3, f"expect 3, got {len(tasks)}"
        assert tasks[0].status == TaskStatus.PENDING, f"expect the tasks[0].status to be {TaskStatus.PENDING}, got {tasks[0].status}"
        assert tasks[1].status == TaskStatus.RUNNING, f"expect the tasks[1].status to be {TaskStatus.RUNNING}, got {tasks[1].status}"
        assert tasks[2].status == TaskStatus.COMPLETED, f"expect the tasks[2].status to be {TaskStatus.COMPLETED}, got {tasks[2].status}"

    def test_task_lifecycle_simulation(self):
        """Test simulating a complete task lifecycle."""
        task = Task(name="Lifecycle Task")
        
        # Initial state
        assert task.status == TaskStatus.PENDING, f"expect the task.status to be {TaskStatus.PENDING}, got {task.status}"
        assert task.start_time is None, f"expect the task.start_time to be {None}, got {task.start_time}"
        assert task.end_time is None, f"expect the task.end_time to be {None}, got {task.end_time}"
        
        # Start task
        task.status = TaskStatus.RUNNING
        task.start_time = datetime.now()
        assert task.status == TaskStatus.RUNNING, f"expect the task.status to be {TaskStatus.RUNNING}, got {task.status}"
        assert task.start_time is not None, f"expect the task.start_time is not None, got {task.start_time}"
        
        # Complete task
        task.status = TaskStatus.COMPLETED
        task.end_time = datetime.now()
        assert task.status == TaskStatus.COMPLETED, f"expect the task.status to be {TaskStatus.COMPLETED}, got {task.status}"
        assert task.end_time is not None, f"expect the task.end_time is not None, got {task.end_time}"
        assert task.end_time >= task.start_time, f"expect the task.end_time >= task.start_time, got {task.end_time}"
