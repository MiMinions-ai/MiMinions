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

    assert wf.run.prompt == "Summarize this PDF", (
        f"expected wf.run.prompt to equal 'Summarize this PDF.', "
        f"but got {wf.run.prompt}"
    )
    assert wf.run.output == "Here is the summary.", (
        f"expected wf.run.output to equal 'Here is the summary.', "
        f"but got {wf.run.output}"
    )
    assert len(wf.run.tool_calls) == 3, (
        f"expected 3 tool calls, but got {len(wf.run.tool_calls)}"
    )
    assert wf.tool_usage_counts()["web_search"] == 2, (
        f"expected 'web_search to be used 2 times, "
        f"but got {wf.tool_usage_counts()}"
    )
    assert wf.most_used_tool() == "web_search", (
        f"expected most used tool to be 'web_search', "
        f"but got {wf.most_used_tool()}"
    )


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

    assert wf2.agent_name == "AgentA", (
        f"expected agent_name to be 'AgentA', but got {wf2.agent_name}"
    )
    assert wf2.run.prompt == "Hello", (
        f"expected run.prompt to be 'Hello', but got {wf2.run.prompt}"
    )
    assert wf2.run.output == "Done",  (
        f"expected run.prompt to be 'Done', but got {wf2.run.output}"
    )
    assert wf2.run.tool_calls[0].tool_name == "calculator", (
        f"expected first tool call to be 'calculator', "
        f"but got {wf2.run.tool_calls[0].tool_name}"
    )
    assert wf2.most_used_tool() == "calculator", (
        f"expected most used tool to be 'calculator', "
        f"but got {wf2.most_used_tool()}"
    )


def test_most_used_tool_none_when_no_calls():
    """
    If no tools were used, most_used_tool() should return None.
    """
    run = AgentRunRecord(prompt="No tools")
    wf = WorkflowRun(agent_name="AgentA", run=run)

    assert wf.most_used_tool() is None, (
        f"expected most_used_tool() to return None when no tool calls exist, "
        f"but got {wf.most_used_tool()}"
    )


def test_tool_call_order_increments():
    """
    Tool calls should automatically increment order.
    """
    run = AgentRunRecord(prompt="Test ordering")

    t1 = run.record_tool_call("tool_a")
    t2 = run.record_tool_call("tool_b")

    assert t1.order == 0, (
        f"expected first tool call order to be 0, but got {t1.order}"
    )
    assert t2.order == 1, (
        f"expected second tool call order to be 1, but got {t2.order}"
    )