import pytest
from miminions.workflow.models import AgentRunRecord, WorkflowRun
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
    from miminions.workflow.models import AgentRunRecord
    run = AgentRunRecord(prompt="Add two numbers")
    controller = WorkflowController(agent, run=run)
    result = controller.execute("calculator", a=2, b=3)
    workflow_run = controller.finish_run("The answer is 5")

    assert result.result == 5, (
        f"expected result.result to be 5, but got {result.result}"
    )
    assert isinstance(workflow_run, WorkflowRun), (
        f"expected workflow_run to be instance of WorkflowRun, "
        f"but got {type(workflow_run)}"
    )
    assert workflow_run.run.prompt == "Add two numbers", (
        f"expected run.prompt to be 'Add two numbers', "
        f"but got {workflow_run.run.prompt}"
    )
    assert workflow_run.run.output == "The answer is 5", (
        f"expected run.output to be 'The answer is 5', "
        f"but got {workflow_run.run.output}"
    )
    assert len(workflow_run.run.tool_calls) == 1, (
        f"expected 1 tool call, but got {len(workflow_run.run.tool_calls)}"
    )
    assert workflow_run.run.tool_calls[0].tool_name == "calculator", (
        f"expected tool_name to be 'calculator', "
        f"but got {workflow_run.run.tool_calls[0].tool_name}"
    )
    assert workflow_run.run.tool_calls[0].result == 5, (
        f"expected tool result to be 5, "
        f"but got {workflow_run.run.tool_calls[0].result}"
    )
    assert workflow_run.run.tool_calls[0].error is None, (
        f"expected no error, but got {workflow_run.run.tool_calls[0].error}"
    )
    assert workflow_run.run.tool_calls[0].status == "success", (
        f"expected status to be 'success', but got {workflow_run.run.tool_calls[0].status}"
    )
    assert workflow_run.run.tool_calls[0].execution_time_ms == 12.5, (
        f"expected execution_time_ms to be 12.5, "
        f"but got {workflow_run.run.tool_calls[0].execution_time_ms}"
    )


def test_controller_records_failed_tool_call():
    agent = MockAgent()
    run = AgentRunRecord(prompt="Try bad tool")
    controller = WorkflowController(agent, run=run)
    result = controller.execute("unknown_tool")
    workflow_run = controller.finish_run("Tool failed")

    assert result.error == "Tool failed", (
        f"expected result.error to be 'Tool failed', but got {result.error}"
    )
    assert len(workflow_run.run.tool_calls) == 1, (
        f"expected 1 tool call, but got {len(workflow_run.run.tool_calls)}"
    )
    assert workflow_run.run.tool_calls[0].tool_name == "unknown_tool", (
        f"expected tool_name to be 'unknown_tool', "
        f"but got {workflow_run.run.tool_calls[0].error}"
    )
    assert workflow_run.run.tool_calls[0].error == "Tool failed", (
        f"expected tool error to be 'Tool failed', "
        f"but got {workflow_run.run.tool_calls[0].error}"
    )
    assert workflow_run.run.tool_calls[0].status == "error", (
        f"expected status to be 'error', "
        f"but got {workflow_run.run.tool_calls[0].status}"
    )


def test_controller_requires_run_at_construction():
    agent = MockAgent()
    with pytest.raises(TypeError):
        controller = WorkflowController(agent)  # run= is now required, no default