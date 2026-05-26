from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from miminions.workflow.models import AgentRunRecord, WorkflowRun, WorkflowTrace

if TYPE_CHECKING:
    from miminions.agent.models import ToolExecutionResult


class WorkflowController:
    """
    Bridge between the Minion agent and workflow tracing.

    The caller is responsible for creating both the AgentRunRecord and
    WorkflowTrace and passing them in. The controller only appends records
    into the trace — it never takes initiative to start a run on its own.

    Typical usage:
        agent_record = AgentRunRecord(prompt="Hello")
        trace = WorkflowTrace()
        controller = WorkflowController(agent, agent_record=agent_record, trace=trace)
        controller.execute("some_tool", arguments={...})
        workflow_run = controller.finish_run(output="Done")
    """

    def __init__(
        self,
        agent: Any,
        agent_record: AgentRunRecord,
        trace: WorkflowTrace,
        agent_name: Optional[str] = None,
    ):
        self._agent = agent
        self._agent_name = agent_name or getattr(agent, "name", "UnknownAgent")
        self._agent_record = agent_record
        self._trace = trace
        self._trace.add_agent_record(agent_record)

    def execute(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        result = self._agent.execute(tool_name, arguments=arguments, **kwargs)
        merged_kwargs = {**(arguments or {}), **kwargs}

        self._trace.add_tool_record(
            tool_name=tool_name,
            kwargs=merged_kwargs,
            result=result.result,
            error=result.error,
            status=str(result.status),
            execution_time_ms=result.execution_time_ms,
        )
        return result

    async def execute_async(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        result = await self._agent.execute_async(tool_name, arguments=arguments, **kwargs)
        merged_kwargs = {**(arguments or {}), **kwargs}

        self._trace.add_tool_record(
            tool_name=tool_name,
            kwargs=merged_kwargs,
            result=result.result,
            error=result.error,
            status=str(result.status),
            execution_time_ms=result.execution_time_ms,
        )
        return result

    def finish_run(self, output: str) -> WorkflowRun:
        self._agent_record.output = output
        return WorkflowRun(
            agent_name=self._agent_name,
            trace=self._trace,
        )