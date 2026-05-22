"""Pydantic models for Tool definitions and executions."""

from enum import Enum
from typing import Any, Dict, List, Optional

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
