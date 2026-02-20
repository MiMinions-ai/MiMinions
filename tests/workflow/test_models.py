import pytest

from miminions.workflow.models import AgentRunRecord, WorkflowRun


def test_records_prompt_tools_and_output():
    """
    Verify we correctly record:
    - prompt
    - tool calls (with order)
    - final output
    - usage statistics
    """
    run = AgentRunRecord(prompt="Summarize this PDF")

    run.record_tool_call(
        "web_search",
        args=["MiMinions"],
        result=["link1", "link2"],
    )

    run.record_tool_call(
        "web_search",
        args=["workflow tracing"],
        result=["link3"],
    )

    run.record_tool_call(
        "calculator",
        kwargs={"a": 2, "b": 3},
        result=5,
    )

    run.output = "Here is the summary."

    wf = WorkflowRun(agent_name="MyAgent", run=run)

    assert wf.run.prompt == "Summarize this PDF"
    assert wf.run.output == "Here is the summary."
    assert len(wf.run.tool_calls) == 3
    assert wf.tool_usage_counts()["web_search"] == 2
    assert wf.most_used_tool() == "web_search"


def test_serialization_round_trip():
    """
    Ensure to_dict() -> from_dict() preserves data.
    """
    run = AgentRunRecord(prompt="Hello")
    run.record_tool_call(
        "calculator",
        kwargs={"a": 1, "b": 2},
        result=3,
    )
    run.output = "Done"

    wf = WorkflowRun(agent_name="AgentA", run=run)

    data = wf.to_dict()
    wf2 = WorkflowRun.from_dict(data)

    assert wf2.agent_name == "AgentA"
    assert wf2.run.prompt == "Hello"
    assert wf2.run.output == "Done"
    assert wf2.run.tool_calls[0].tool_name == "calculator"
    assert wf2.most_used_tool() == "calculator"


def test_most_used_tool_none_when_no_calls():
    """
    If no tools were used, most_used_tool() should return None.
    """
    run = AgentRunRecord(prompt="No tools")
    wf = WorkflowRun(agent_name="AgentA", run=run)

    assert wf.most_used_tool() is None


def test_tool_call_order_increments():
    """
    Tool calls should automatically increment order.
    """
    run = AgentRunRecord(prompt="Test ordering")

    t1 = run.record_tool_call("tool_a")
    t2 = run.record_tool_call("tool_b")

    assert t1.order == 0
    assert t2.order == 1