from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Union
from uuid import uuid4
from collections import Counter


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ToolCallRecord:
    """
    One tool invocation: what tool was called, its inputs, and what came back.
    Scope is limited to tool-level input/output only.
    """
    tool_name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    result: Any = None
    error: Optional[str] = None
    status: Optional[str] = None
    execution_time_ms: Optional[float] = None

    order: int = 0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "tool",
            "tool_name": self.tool_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "result": self.result,
            "error": self.error,
            "order": self.order,
            "timestamp": self.timestamp,
            "status": self.status,
            "execution_time_ms": self.execution_time_ms,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "ToolCallRecord":
        return ToolCallRecord(
            tool_name=data["tool_name"],
            args=list(data.get("args", [])),
            kwargs=dict(data.get("kwargs", {})),
            result=data.get("result"),
            error=data.get("error"),
            order=int(data.get("order", 0)),
            timestamp=data.get("timestamp") or _now_iso(),
            status=data.get("status"),
            execution_time_ms=data.get("execution_time_ms"),
        )


@dataclass
class AgentRunRecord:
    """
    One agent turn: prompt in, output out.
    Scope is limited to agent-level input/output only.
    Tool calls are no longer nested here — they live in WorkflowTrace.
    """
    prompt: str
    output: Optional[str] = None

    id: str = field(default_factory=lambda: f"run_{uuid4().hex}")
    created_at: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "type": "agent",
            "id": self.id,
            "created_at": self.created_at,
            "prompt": self.prompt,
            "output": self.output,
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AgentRunRecord":
        return AgentRunRecord(
            id=data.get("id") or f"run_{uuid4().hex}",
            created_at=data.get("created_at") or _now_iso(),
            prompt=data["prompt"],
            output=data.get("output"),
        )


# A record in the trace is either an agent turn or a tool call
WorkflowRecord = Union[AgentRunRecord, ToolCallRecord]


@dataclass
class WorkflowTrace:
    """
    Ordered collection of agent and tool records.
    This is the single source of truth for what happened and in what sequence.
    """
    records: List[WorkflowRecord] = field(default_factory=list)

    def add_agent_record(self, record: AgentRunRecord) -> None:
        self.records.append(record)

    def add_tool_record(
        self,
        tool_name: str,
        *,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        result: Any = None,
        error: Optional[str] = None,
        status: Optional[str] = None,
        execution_time_ms: Optional[float] = None,
    ) -> ToolCallRecord:
        rec = ToolCallRecord(
            tool_name=tool_name,
            args=[] if args is None else list(args),
            kwargs={} if kwargs is None else dict(kwargs),
            result=result,
            error=error,
            order=len(self.records),
            status=status,
            execution_time_ms=execution_time_ms,
        )
        self.records.append(rec)
        return rec

    def tool_usage_counts(self) -> Dict[str, int]:
        c = Counter(
            r.tool_name for r in self.records if isinstance(r, ToolCallRecord)
        )
        return dict(c)

    def most_used_tool(self) -> Optional[str]:
        counts = self.tool_usage_counts()
        if not counts:
            return None
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def to_dict(self) -> List[Dict[str, Any]]:
        return [r.to_dict() for r in self.records]

    @staticmethod
    def from_dict(data: List[Dict[str, Any]]) -> "WorkflowTrace":
        trace = WorkflowTrace()
        for entry in data:
            if entry.get("type") == "agent":
                trace.records.append(AgentRunRecord.from_dict(entry))
            elif entry.get("type") == "tool":
                trace.records.append(ToolCallRecord.from_dict(entry))
        return trace


@dataclass
class WorkflowRun:
    """
    A completed workflow run: who ran it and the full trace of what happened.
    """
    agent_name: str
    trace: WorkflowTrace

    id: str = field(default_factory=lambda: f"wf_{uuid4().hex}")
    schema_version: int = 2
    created_at: str = field(default_factory=_now_iso)

    def most_used_tool(self) -> Optional[str]:
        return self.trace.most_used_tool()

    def tool_usage_counts(self) -> Dict[str, int]:
        return self.trace.tool_usage_counts()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "created_at": self.created_at,
            "agent_name": self.agent_name,
            "trace": self.trace.to_dict(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WorkflowRun":
        return WorkflowRun(
            id=data.get("id") or f"wf_{uuid4().hex}",
            created_at=data.get("created_at") or _now_iso(),
            schema_version=int(data.get("schema_version", 2)),
            agent_name=data["agent_name"],
            trace=WorkflowTrace.from_dict(data["trace"]),
        )