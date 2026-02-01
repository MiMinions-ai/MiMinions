"""Pydantic models for the Agent.

Uses pydantic BaseModel for validation. These models are compatible with pydantic_ai
and provide structured data types for tool definitions, execution results, and memory.
"""

from typing import Any, Dict, List, Optional
from enum import Enum
from datetime import datetime
from pydantic import BaseModel, Field


class ParameterType(str, Enum):
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Tool parameter definition."""
    name: str
    type: ParameterType = ParameterType.STRING
    description: str = ""
    required: bool = True
    default: Optional[Any] = None
    model_config = {"extra": "forbid"}


class ToolSchema(BaseModel):
    """Tool parameters schema with JSON Schema conversion."""
    parameters: List[ToolParameter] = Field(default_factory=list)
    model_config = {"extra": "forbid"}

    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format."""
        props = {}
        req = []
        for p in self.parameters:
            props[p.name] = {"type": p.type.value, "description": p.description}
            if p.default is not None:
                props[p.name]["default"] = p.default
            if p.required:
                req.append(p.name)
        return {"type": "object", "properties": props, "required": req}


class ToolDefinition(BaseModel):
    """Complete tool definition with schema."""
    name: str
    description: str
    schema_def: ToolSchema = Field(default_factory=ToolSchema, alias="schema")
    model_config = {"extra": "forbid", "populate_by_name": True}

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dict for LLM tool calling."""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.schema_def.to_json_schema(),
        }


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool."""
    tool_name: str
    arguments: Dict[str, Any] = Field(default_factory=dict)
    model_config = {"extra": "forbid"}


class ExecutionStatus(str, Enum):
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


class ToolExecutionResult(BaseModel):
    """Result of tool execution with status and timing."""
    tool_name: str
    status: ExecutionStatus
    result: Optional[Any] = None
    error_message: Optional[str] = Field(default=None, alias="error")
    execution_time_ms: Optional[float] = None
    model_config = {"extra": "forbid", "populate_by_name": True}

    @property
    def error(self) -> Optional[str]:
        return self.error_message

    @classmethod
    def success(cls, tool_name: str, result: Any, execution_time_ms: Optional[float] = None):
        return cls(tool_name=tool_name, status=ExecutionStatus.SUCCESS, result=result, execution_time_ms=execution_time_ms)

    @classmethod
    def from_error(cls, tool_name: str, error: str, execution_time_ms: Optional[float] = None):
        return cls(tool_name=tool_name, status=ExecutionStatus.ERROR, error_message=error, execution_time_ms=execution_time_ms)


class AgentConfig(BaseModel):
    """Agent configuration."""
    name: str
    description: str = ""
    chunk_size: int = Field(default=800, ge=100, le=10000)
    overlap: int = Field(default=150, ge=0, le=500)
    model_config = {"extra": "forbid"}


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


class AgentState(BaseModel):
    """Current agent state snapshot."""
    config: AgentConfig
    tool_count: int = 0
    has_memory: bool = False
    connected_servers: List[str] = Field(default_factory=list)
    model_config = {"extra": "forbid"}
