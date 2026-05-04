from __future__ import annotations

from typing import Any, Dict, Optional, TYPE_CHECKING

from miminions.workflow.models import AgentRunRecord, WorkflowRun

if TYPE_CHECKING:
    from miminions.agent.models import ToolExecutionResult


class WorkflowController:
    """
    Bridge between the Minion agent and workflow tracing.

    The caller is responsible for creating the AgentRunRecord and passing it in.
    The controller only appends tool call records and finalises the WorkflowRun —
    it never takes the initiative to start a run on its own.

    Typical usage:
        run = AgentRunRecord(prompt="Hello")
        controller = WorkflowController(agent, run=run)
        controller.execute("some_tool", arguments={...})
        workflow_run = controller.finish_run(output="Done")
    """

    def __init__(
        self,
        agent: Any,
        run: AgentRunRecord,
        agent_name: Optional[str] = None,
    ):
        self._agent = agent
        self._agent_name = agent_name or getattr(agent, "name", "UnknownAgent")
        self._current_record: AgentRunRecord = run

    # ------------------------------------------------------------------
    # Backward-compat shim — lets existing call sites keep working while
    # we migrate them.  Mark deprecated so reviewers/linters can flag it.
    # ------------------------------------------------------------------
    @classmethod
    def from_prompt(
        cls,
        agent: Any,
        prompt: str,
        agent_name: Optional[str] = None,
    ) -> "WorkflowController":
        """
        Convenience constructor that creates the AgentRunRecord externally
        and passes it in.  Prefer constructing AgentRunRecord yourself and
        calling WorkflowController(agent, run=run) directly.

        Deprecated: will be removed once all call-sites are migrated.
        """
        run = AgentRunRecord(prompt=prompt)
        return cls(agent, run=run, agent_name=agent_name)

    def execute(
        self,
        tool_name: str,
        arguments: Optional[Dict[str, Any]] = None,
        **kwargs: Any,
    ) -> Any:
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
        self._current_record.output = output
        return WorkflowRun(
            agent_name=self._agent_name,
            run=self._current_record,
        )