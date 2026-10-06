"""Serializable contracts for the local execution service."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, TYPE_CHECKING
import os

if TYPE_CHECKING:
    from .service import ExecutionService

TERMINAL = frozenset({"completed", "failed", "cancelled"})


def conversation_key(workspace_id: str, session_id: str) -> str:
    """Match transcript filename normalization, including Windows case aliases."""
    return f"workspace:{workspace_id}:session:{os.path.normcase(session_id.strip())}"


@dataclass(frozen=True)
class ExecutionRequest:
    kind: str
    params: dict[str, Any] = field(default_factory=dict)
    cwd: str = ""
    session_key: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ExecutionRequest:
        return cls(**value)


@dataclass(frozen=True)
class ExecutionTask:
    id: str
    request: ExecutionRequest
    status: str
    created_at: str
    started_at: str | None = None
    ended_at: str | None = None
    result: Any = None
    error: str | None = None
    cancel_requested: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {**asdict(self), "kind": "execution"}

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> ExecutionTask:
        fields = {key: item for key, item in value.items() if key != "kind"}
        fields["request"] = ExecutionRequest.from_dict(fields["request"])
        return cls(**fields)


@dataclass(frozen=True)
class TaskEvent:
    task_id: str
    sequence: int
    timestamp: str
    type: str
    data: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> TaskEvent:
        return cls(**value)


@dataclass(frozen=True)
class TaskHandle:
    id: str
    service: ExecutionService = field(repr=False, compare=False)

    def get(self) -> ExecutionTask:
        return self.service.get(self.id)

    def follow(self, after: int = 0):
        return self.service.follow(self.id, after)

    def cancel(self) -> None:
        self.service.cancel(self.id)

    def release(self) -> None:
        self.service.store.release(self.id)

    def to_dict(self) -> dict[str, str]:
        return {"id": self.id}

    @classmethod
    def from_dict(cls, value: dict[str, str], service: ExecutionService | None = None) -> TaskHandle:
        if service is None:
            from .service import ExecutionService
            service = ExecutionService()
        return cls(value["id"], service)
