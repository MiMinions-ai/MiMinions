import pytest

from miminions.workflow.models import AgentRunRecord, WorkflowRun, WorkflowTrace, ToolCallRecord


def test_records_prompt_tools_and_output():
    """
    Verify we correctly record:
    - prompt
    - tool calls (with order)
    - final output
    - usage statistics
    """
    agent_record = AgentRunRecord(prompt="Summarize this PDF")
    trace = WorkflowTrace()
    trace.add_agent_record(agent_record)

    trace.add_tool_record("web_search", args=["MiMinions"], result=["link1", "link2"])
    trace.add_tool_record("web_search", args=["workflow tracing"], result=["link3"])
    trace.add_tool_record("calculator", kwargs={"a": 2, "b": 3}, result=5)

    agent_record.output = "Here is the summary."

    wf = WorkflowRun(agent_name="MyAgent", trace=trace)

    stored_agent = next(r for r in wf.trace.records if isinstance(r, AgentRunRecord))
    tool_calls = [r for r in wf.trace.records if isinstance(r, ToolCallRecord)]

    assert stored_agent.prompt == "Summarize this PDF", (
        f"expected prompt to equal 'Summarize this PDF', "
        f"but got {stored_agent.prompt}"
    )
    assert stored_agent.output == "Here is the summary.", (
        f"expected output to equal 'Here is the summary.', "
        f"but got {stored_agent.output}"
    )
    assert len(tool_calls) == 3, (
        f"expected 3 tool calls, but got {len(tool_calls)}"
    )
    assert wf.tool_usage_counts()["web_search"] == 2, (
        f"expected 'web_search' to be used 2 times, "
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
    agent_record = AgentRunRecord(prompt="Hello")
    trace = WorkflowTrace()
    trace.add_agent_record(agent_record)
    trace.add_tool_record("calculator", kwargs={"a": 1, "b": 2}, result=3)
    agent_record.output = "Done"

    wf = WorkflowRun(agent_name="AgentA", trace=trace)

    data = wf.to_dict()
    wf2 = WorkflowRun.from_dict(data)

    stored_agent = next(r for r in wf2.trace.records if isinstance(r, AgentRunRecord))
    tool_calls = [r for r in wf2.trace.records if isinstance(r, ToolCallRecord)]

    assert wf2.agent_name == "AgentA", (
        f"expected agent_name to be 'AgentA', but got {wf2.agent_name}"
    )
    assert stored_agent.prompt == "Hello", (
        f"expected prompt to be 'Hello', but got {stored_agent.prompt}"
    )
    assert stored_agent.output == "Done", (
        f"expected output to be 'Done', but got {stored_agent.output}"
    )
    assert tool_calls[0].tool_name == "calculator", (
        f"expected first tool call to be 'calculator', "
        f"but got {tool_calls[0].tool_name}"
    )
    assert wf2.most_used_tool() == "calculator", (
        f"expected most used tool to be 'calculator', "
        f"but got {wf2.most_used_tool()}"
    )


def test_most_used_tool_none_when_no_calls():
    """
    If no tools were used, most_used_tool() should return None.
    """
    agent_record = AgentRunRecord(prompt="No tools")
    trace = WorkflowTrace()
    trace.add_agent_record(agent_record)
    wf = WorkflowRun(agent_name="AgentA", trace=trace)

    assert wf.most_used_tool() is None, (
        f"expected most_used_tool() to return None when no tool calls exist, "
        f"but got {wf.most_used_tool()}"
    )


def test_tool_call_order_increments():
    """
    Tool calls should automatically increment order based on position in trace.
    """
    agent_record = AgentRunRecord(prompt="Test ordering")
    trace = WorkflowTrace()
    trace.add_agent_record(agent_record)

    t1 = trace.add_tool_record("tool_a")
    t2 = trace.add_tool_record("tool_b")

    assert t1.order == 1, (
        f"expected first tool call order to be 1, but got {t1.order}"
    )
    assert t2.order == 2, (
        f"expected second tool call order to be 2, but got {t2.order}"
    )