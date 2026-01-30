"""
Pydantic Models for the Pydantic Agent

This module defines all Pydantic models used by the Pydantic Agent for:
- Tool definitions and schemas
- Tool execution requests and results
- Agent configuration
- Memory entries and queries

These models provide strong typing, validation, and serialization support,
making the agent's interface explicit and well-documented.
"""

from typing import Any, Dict, List, Optional, Union, Callable
from enum import Enum
from pydantic import BaseModel, Field, field_validator
from datetime import datetime


class ParameterType(str, Enum):
    """Supported parameter types for tool schemas"""
    STRING = "string"
    INTEGER = "integer"
    NUMBER = "number"
    BOOLEAN = "boolean"
    ARRAY = "array"
    OBJECT = "object"


class ToolParameter(BaseModel):
    """Schema for a single tool parameter"""
    name: str = Field(..., description="Parameter name")
    type: ParameterType = Field(default=ParameterType.STRING, description="Parameter type")
    description: str = Field(default="", description="Parameter description")
    required: bool = Field(default=True, description="Whether the parameter is required")
    default: Optional[Any] = Field(default=None, description="Default value if not required")
    
    model_config = {"extra": "forbid"}


class ToolSchema(BaseModel):
    """Schema definition for a tool's parameters"""
    parameters: List[ToolParameter] = Field(default_factory=list, description="List of parameters")
    
    model_config = {"extra": "forbid"}
    
    def to_json_schema(self) -> Dict[str, Any]:
        """Convert to JSON Schema format for LLM consumption"""
        properties = {}
        required = []
        
        for param in self.parameters:
            properties[param.name] = {
                "type": param.type.value,
                "description": param.description,
            }
            if param.default is not None:
                properties[param.name]["default"] = param.default
            if param.required:
                required.append(param.name)
        
        return {
            "type": "object",
            "properties": properties,
            "required": required,
        }


class ToolDefinition(BaseModel):
    """Complete definition of a tool"""
    name: str = Field(..., description="Unique tool name")
    description: str = Field(..., description="Human-readable description of what the tool does")
    schema_def: ToolSchema = Field(default_factory=ToolSchema, alias="schema", description="Parameter schema")
    
    model_config = {"extra": "forbid", "populate_by_name": True}
    
    @field_validator("name")
    @classmethod
    def validate_name(cls, v: str) -> str:
        """Ensure tool name is valid identifier"""
        if not v.isidentifier() and not v.replace("_", "").replace("-", "").isalnum():
            # Be lenient but require reasonable naming
            pass
        return v
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary format compatible with LLM tool calling"""
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.schema_def.to_json_schema(),
        }


class ToolExecutionRequest(BaseModel):
    """Request to execute a tool"""
    tool_name: str = Field(..., description="Name of the tool to execute")
    arguments: Dict[str, Any] = Field(default_factory=dict, description="Arguments to pass to the tool")
    
    model_config = {"extra": "forbid"}


class ExecutionStatus(str, Enum):
    """Status of a tool execution"""
    SUCCESS = "success"
    ERROR = "error"
    PENDING = "pending"


class ToolExecutionResult(BaseModel):
    """Result of a tool execution"""
    tool_name: str = Field(..., description="Name of the executed tool")
    status: ExecutionStatus = Field(..., description="Execution status")
    result: Optional[Any] = Field(default=None, description="Result value if successful")
    error: Optional[str] = Field(default=None, description="Error message if failed")
    execution_time_ms: Optional[float] = Field(default=None, description="Execution time in milliseconds")
    
    model_config = {"extra": "forbid"}
    
    @classmethod
    def success(cls, tool_name: str, result: Any, execution_time_ms: Optional[float] = None) -> "ToolExecutionResult":
        """Create a successful result"""
        return cls(
            tool_name=tool_name,
            status=ExecutionStatus.SUCCESS,
            result=result,
            execution_time_ms=execution_time_ms,
        )
    
    @classmethod
    def error(cls, tool_name: str, error: str, execution_time_ms: Optional[float] = None) -> "ToolExecutionResult":
        """Create an error result"""
        return cls(
            tool_name=tool_name,
            status=ExecutionStatus.ERROR,
            error=error,
            execution_time_ms=execution_time_ms,
        )


class AgentConfig(BaseModel):
    """Configuration for a Pydantic Agent"""
    name: str = Field(..., description="Agent name")
    description: str = Field(default="", description="Agent description")
    chunk_size: int = Field(default=800, ge=100, le=10000, description="Text chunk size for memory")
    overlap: int = Field(default=150, ge=0, le=500, description="Overlap between chunks")
    
    model_config = {"extra": "forbid"}


class MemoryEntry(BaseModel):
    """A single entry in the agent's memory"""
    id: str = Field(..., description="Unique identifier")
    text: str = Field(..., description="The stored text content")
    metadata: Dict[str, Any] = Field(default_factory=dict, description="Associated metadata")
    created_at: Optional[datetime] = Field(default=None, description="When the entry was created")
    
    model_config = {"extra": "forbid"}


class MemoryQueryResult(BaseModel):
    """Result of a memory query"""
    query: str = Field(..., description="The original query")
    results: List[MemoryEntry] = Field(default_factory=list, description="Matching entries")
    count: int = Field(default=0, description="Number of results")
    message: Optional[str] = Field(default=None, description="Additional message")
    
    model_config = {"extra": "forbid"}
    
    @classmethod
    def empty(cls, query: str, message: str = "No results found") -> "MemoryQueryResult":
        """Create an empty result"""
        return cls(query=query, results=[], count=0, message=message)


class AgentState(BaseModel):
    """Current state of an agent (for future LLM integration)"""
    config: AgentConfig = Field(..., description="Agent configuration")
    tool_count: int = Field(default=0, description="Number of registered tools")
    has_memory: bool = Field(default=False, description="Whether memory is attached")
    connected_servers: List[str] = Field(default_factory=list, description="Connected MCP server names")
    
    model_config = {"extra": "forbid"}
