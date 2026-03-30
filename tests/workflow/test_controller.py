import pytest

from miminions.workflow.controller import WorkflowController
from miminions.workflow.models import WorkflowRun


class FakeToolExecutionResult:
    def __init__(self, tool_name, status, result=None, error=None, execution_time_ms=None):
        self.tool_name = tool_name
        self.status = status
        self.result = result
        self.error = error
        self.execution_time_ms = execution_time_ms


class MockAgent:
    def __init__(self, name="MockAgent"):
        self.name = name

    def execute(self, tool_name, arguments=None, **kwargs):
        merged = {**(arguments or {}), **kwargs}
        if tool_name == "calculator":
            return FakeToolExecutionResult(
                tool_name=tool_name,
                status="success",
                result=merged["a"] + merged["b"],
                execution_time_ms=12.5,
            )
        return FakeToolExecutionResult(
            tool_name=tool_name,
            status="error",
            error="Tool failed",
            execution_time_ms=5.0,
        )


def test_controller_records_successful_tool_call():
    agent = MockAgent()
    controller = WorkflowController(agent)

    controller.start_run("Add two numbers")
    result = controller.execute("calculator", a=2, b=3)
    workflow_run = controller.finish_run("The answer is 5")

    assert result.result == 5
    assert isinstance(workflow_run, WorkflowRun)
    assert workflow_run.run.prompt == "Add two numbers"
    assert workflow_run.run.output == "The answer is 5"
    assert len(workflow_run.run.tool_calls) == 1
    assert workflow_run.run.tool_calls[0].tool_name == "calculator"
    assert workflow_run.run.tool_calls[0].result == 5
    assert workflow_run.run.tool_calls[0].error is None
    assert workflow_run.run.tool_calls[0].status == "success"
    assert workflow_run.run.tool_calls[0].execution_time_ms == 12.5


def test_controller_records_failed_tool_call():
    agent = MockAgent()
    controller = WorkflowController(agent)

    controller.start_run("Try bad tool")
    result = controller.execute("unknown_tool")
    workflow_run = controller.finish_run("Tool failed")

    assert result.error == "Tool failed"
    assert len(workflow_run.run.tool_calls) == 1
    assert workflow_run.run.tool_calls[0].tool_name == "unknown_tool"
    assert workflow_run.run.tool_calls[0].error == "Tool failed"
    assert workflow_run.run.tool_calls[0].status == "error"


def test_controller_requires_start_run():
    agent = MockAgent()
    controller = WorkflowController(agent)

    with pytest.raises(RuntimeError):
        controller.execute("calculator", a=1, b=2)