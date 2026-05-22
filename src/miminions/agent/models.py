"""Pydantic models for the Agent configuration and state."""

from typing import List

from pydantic import BaseModel, Field


class AgentConfig(BaseModel):
    """Agent configuration."""
    name: str
    description: str = ""
    chunk_size: int = Field(default=800, ge=100, le=10000)
    overlap: int = Field(default=150, ge=0, le=500)
    model_config = {"extra": "forbid"}


class AgentState(BaseModel):
    """Current agent state snapshot."""
    config: AgentConfig
    tool_count: int = 0
    has_memory: bool = False
    connected_servers: List[str] = Field(default_factory=list)
    model_config = {"extra": "forbid"}
