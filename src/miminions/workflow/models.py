from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4
from collections import Counter


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


@dataclass
class ToolCallRecord:
    """
    One tool invocation made by the agent.
    Stores what tool was used, the inputs, and what came back.
    """
    tool_name: str
    args: List[Any] = field(default_factory=list)
    kwargs: Dict[str, Any] = field(default_factory=dict)

    # What happened
    result: Any = None
    error: Optional[str] = None

    # Ordering + timestamp for traceability
    order: int = 0
    timestamp: str = field(default_factory=_now_iso)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "args": self.args,
            "kwargs": self.kwargs,
            "result": self.result,
            "error": self.error,
            "order": self.order,
            "timestamp": self.timestamp,
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
        )


@dataclass
class AgentRunRecord:
    """
    One agent run: prompt in, tool calls during, output out.
    """
    prompt: str
    output: Optional[str] = None
    tool_calls: List[ToolCallRecord] = field(default_factory=list)

    id: str = field(default_factory=lambda: f"run_{uuid4().hex}")
    created_at: str = field(default_factory=_now_iso)

    def record_tool_call(
        self,
        tool_name: str,
        *,
        args: Optional[List[Any]] = None,
        kwargs: Optional[Dict[str, Any]] = None,
        result: Any = None,
        error: Optional[str] = None,
    ) -> ToolCallRecord:
        """
        Append a tool call record in order. Returns the created record.
        """
        rec = ToolCallRecord(
            tool_name=tool_name,
            args=[] if args is None else list(args),
            kwargs={} if kwargs is None else dict(kwargs),
            result=result,
            error=error,
            order=len(self.tool_calls),
        )
        self.tool_calls.append(rec)
        return rec

    def tool_usage_counts(self) -> Dict[str, int]:
        """
        Returns counts of tool usage, e.g. {"calculator": 3, "search": 1}.
        """
        c = Counter(tc.tool_name for tc in self.tool_calls)
        return dict(c)

    def most_used_tool(self) -> Optional[str]:
        """
        Returns the most commonly used tool name. None if no tool calls exist.
        If there's a tie, returns one of the top tools (stable enough for now).
        """
        counts = self.tool_usage_counts()
        if not counts:
            return None
        return max(counts.items(), key=lambda kv: kv[1])[0]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "created_at": self.created_at,
            "prompt": self.prompt,
            "output": self.output,
            "tool_calls": [tc.to_dict() for tc in self.tool_calls],
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "AgentRunRecord":
        run = AgentRunRecord(
            id=data.get("id") or f"run_{uuid4().hex}",
            created_at=data.get("created_at") or _now_iso(),
            prompt=data["prompt"],
            output=data.get("output"),
        )
        for tc in data.get("tool_calls", []):
            run.tool_calls.append(ToolCallRecord.from_dict(tc))
        return run


@dataclass
class WorkflowRun:
    """
    Simple wrapper around an agent run trace.
    If you only need ONE run, keep it as 'run'.
    """
    agent_name: str
    run: AgentRunRecord

    id: str = field(default_factory=lambda: f"wf_{uuid4().hex}")
    schema_version: int = 1
    created_at: str = field(default_factory=_now_iso)

    def most_used_tool(self) -> Optional[str]:
        return self.run.most_used_tool()

    def tool_usage_counts(self) -> Dict[str, int]:
        return self.run.tool_usage_counts()

    def to_dict(self) -> Dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "id": self.id,
            "created_at": self.created_at,
            "agent_name": self.agent_name,
            "run": self.run.to_dict(),
        }

    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "WorkflowRun":
        return WorkflowRun(
            id=data.get("id") or f"wf_{uuid4().hex}",
            created_at=data.get("created_at") or _now_iso(),
            schema_version=int(data.get("schema_version", 1)),
            agent_name=data["agent_name"],
            run=AgentRunRecord.from_dict(data["run"]),
        )
