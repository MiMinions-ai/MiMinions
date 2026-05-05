"""Pydantic models for memory entries."""

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class MemoryEntry(BaseModel):
    """A memory entry."""
    id: str
    text: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: Optional[datetime] = None
    model_config = {"extra": "forbid"}


class MemoryQueryResult(BaseModel):
    """Memory query result with entries."""
    query: str
    results: List[MemoryEntry] = Field(default_factory=list)
    count: int = 0
    message: Optional[str] = None
    model_config = {"extra": "forbid"}

    @classmethod
    def empty(cls, query: str, message: str = "No results found"):
        return cls(query=query, results=[], count=0, message=message)
