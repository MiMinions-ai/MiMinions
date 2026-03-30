from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from miminions.workflow.models import AgentRunRecord, WorkflowRun

if TYPE_CHECKING:
    from miminions.agent.models import ToolExecutionResult


class WorkflowController:
    """
    Bridge between the Minion agent and workflow tracing.
    """

    def __init__(self, agent: Any, agent_name: Optional[str] = None):
        self._agent = agent
        self._agent_name = agent_name or getattr(agent, "name", "UnknownAgent")
        self._current_record: Optional[AgentRunRecord] = None

    def start_run(self, prompt: str) -> AgentRunRecord:
        self._current_record = AgentRunRecord(prompt=prompt)
        return self._current_record

    def execute(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
        if self._current_record is None:
            raise RuntimeError("Call start_run() before execute().")

        result = self._agent.execute(tool_name, arguments=arguments, **kwargs)
        merged_kwargs = {**(arguments or {}), **kwargs}

        self._current_record.record_tool_call(
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
        if self._current_record is None:
            raise RuntimeError("Call start_run() before execute_async().")

        result = await self._agent.execute_async(tool_name, arguments=arguments, **kwargs)
        merged_kwargs = {**(arguments or {}), **kwargs}

        self._current_record.record_tool_call(
            tool_name=tool_name,
            kwargs=merged_kwargs,
            result=result.result,
            error=result.error,
            status=str(result.status),
            execution_time_ms=result.execution_time_ms,
        )
        return result

    def finish_run(self, output: str) -> WorkflowRun:
        if self._current_record is None:
            raise RuntimeError("Call start_run() before finish_run().")

        self._current_record.output = output
        workflow_run = WorkflowRun(
            agent_name=self._agent_name,
            run=self._current_record,
        )
        self._current_record = None
        return workflow_run