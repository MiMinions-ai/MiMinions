import pytest

from miminions.workflow.controller import WorkflowController
from miminions.workflow.models import (
    AgentRunRecord,
    ToolCallRecord,
    WorkflowRun,
    WorkflowTrace,
)


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
    agent_record = AgentRunRecord(prompt="Add two numbers")
    trace = WorkflowTrace()
    controller = WorkflowController(agent, agent_record=agent_record, trace=trace)
    result = controller.execute("calculator", a=2, b=3)
    workflow_run = controller.finish_run("The answer is 5")

    tool_calls = [r for r in workflow_run.trace.records if isinstance(r, ToolCallRecord)]
    agent_record = next(r for r in workflow_run.trace.records if isinstance(r, AgentRunRecord))

    assert result.result == 5, (
        f"expected result.result to be 5, but got {result.result}"
    )
    assert isinstance(workflow_run, WorkflowRun), (
        f"expected workflow_run to be instance of WorkflowRun, "
        f"but got {type(workflow_run)}"
    )
    assert agent_record.prompt == "Add two numbers", (
        f"expected prompt to be 'Add two numbers', "
        f"but got {agent_record.prompt}"
    )
    assert agent_record.output == "The answer is 5", (
        f"expected output to be 'The answer is 5', "
        f"but got {agent_record.output}"
    )
    assert len(tool_calls) == 1, (
        f"expected 1 tool call, but got {len(tool_calls)}"
    )
    assert tool_calls[0].tool_name == "calculator", (
        f"expected tool_name to be 'calculator', "
        f"but got {tool_calls[0].tool_name}"
    )
    assert tool_calls[0].result == 5, (
        f"expected tool result to be 5, "
        f"but got {tool_calls[0].result}"
    )
    assert tool_calls[0].error is None, (
        f"expected no error, but got {tool_calls[0].error}"
    )
    assert tool_calls[0].status == "success", (
        f"expected status to be 'success', but got {tool_calls[0].status}"
    )
    assert tool_calls[0].execution_time_ms == 12.5, (
        f"expected execution_time_ms to be 12.5, "
        f"but got {tool_calls[0].execution_time_ms}"
    )


def test_controller_records_failed_tool_call():
    agent = MockAgent()
    agent_record = AgentRunRecord(prompt="Try bad tool")
    trace = WorkflowTrace()
    controller = WorkflowController(agent, agent_record=agent_record, trace=trace)
    result = controller.execute("unknown_tool")
    workflow_run = controller.finish_run("Tool failed")

    tool_calls = [r for r in workflow_run.trace.records if isinstance(r, ToolCallRecord)]

    assert result.error == "Tool failed", (
        f"expected result.error to be 'Tool failed', but got {result.error}"
    )
    assert len(tool_calls) == 1, (
        f"expected 1 tool call, but got {len(tool_calls)}"
    )
    assert tool_calls[0].tool_name == "unknown_tool", (
        f"expected tool_name to be 'unknown_tool', "
        f"but got {tool_calls[0].tool_name}"
    )
    assert tool_calls[0].error == "Tool failed", (
        f"expected tool error to be 'Tool failed', "
        f"but got {tool_calls[0].error}"
    )
    assert tool_calls[0].status == "error", (
        f"expected status to be 'error', "
        f"but got {tool_calls[0].status}"
    )


def test_controller_requires_run_at_construction():
    agent = MockAgent()
    with pytest.raises(TypeError):
        WorkflowController(agent)
