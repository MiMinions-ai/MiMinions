"""
Task entities and data models for the multi-agent runtime system.

Based on spec 004 (Multi-Agent Runtime System) data model.
"""

from datetime import datetime
from enum import Enum
from typing import Optional
from pydantic import BaseModel, Field, field_validator, model_validator


class TaskStatus(str, Enum):
    """Task execution state."""
    PENDING = "pending"      # Waiting in queue
    RUNNING = "running"      # Currently executing
    COMPLETED = "completed"  # Successfully finished
    FAILED = "failed"        # Execution failed
    CANCELLED = "cancelled"  # User-cancelled before completion


class Task(BaseModel):
    """
    Represents a unit of work to be executed by an agent.

    Per spec 004 requirements (FR-002, FR-003, FR-010).
    """
    task_id: str = Field(..., description="UUID v4 format unique identifier")
    name: str = Field(..., min_length=1, max_length=200, description="Human-readable task name")
    priority: int = Field(50, ge=0, le=100, description="Execution priority (0=highest, 100=lowest)")
    status: TaskStatus = Field(default=TaskStatus.PENDING, description="Current execution state")
    assigned_agent_id: Optional[str] = Field(None, description="Agent currently executing this task")
    input_data: dict = Field(default_factory=dict, description="Input parameters for task execution")
    output_data: Optional[dict] = Field(None, description="Task execution results (null until completed)")
    created_at: datetime = Field(default_factory=datetime.now, description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Execution start time")
    completed_at: Optional[datetime] = Field(None, description="Execution completion time")
    timeout_seconds: Optional[int] = Field(None, gt=0, description="Max execution time (null = no timeout)")
    retry_count: int = Field(0, ge=0, description="Number of retry attempts (starts at 0)")
    max_retries: int = Field(0, ge=0, description="Maximum allowed retries (0 = no retries)")
    error_message: Optional[str] = Field(None, max_length=2000, description="Error details if status=failed")

    @field_validator('started_at')
    @classmethod
    def started_after_created(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate started_at is after created_at."""
        if v and 'created_at' in info.data and v < info.data['created_at']:
            raise ValueError('started_at must be >= created_at')
        return v

    @field_validator('completed_at')
    @classmethod
    def completed_after_started(cls, v: Optional[datetime], info) -> Optional[datetime]:
        """Validate completed_at is after started_at."""
        if v and 'started_at' in info.data and info.data['started_at'] and v < info.data['started_at']:
            raise ValueError('completed_at must be >= started_at')
        return v

    @model_validator(mode='after')
    def validate_cross_fields(self):
        """Validate cross-field constraints."""
        # Validate retry_count <= max_retries
        if self.retry_count > self.max_retries:
            raise ValueError('retry_count must be <= max_retries')
        return self

    @field_validator('assigned_agent_id')
    @classmethod
    def agent_required_when_running(cls, v: Optional[str], info) -> Optional[str]:
        """Validate assigned_agent_id is non-null when status=running."""
        if 'status' in info.data and info.data['status'] == TaskStatus.RUNNING and v is None:
            raise ValueError('assigned_agent_id required when status=running')
        return v

    @field_validator('output_data')
    @classmethod
    def output_only_when_completed(cls, v: Optional[dict], info) -> Optional[dict]:
        """Validate output_data only exists when completed."""
        if v is not None and 'status' in info.data and info.data['status'] != TaskStatus.COMPLETED:
            raise ValueError('output_data should only be set when status=completed')
        return v

    @field_validator('error_message')
    @classmethod
    def error_only_when_failed(cls, v: Optional[str], info) -> Optional[str]:
        """Validate error_message only exists when failed."""
        if v is not None and 'status' in info.data and info.data['status'] != TaskStatus.FAILED:
            raise ValueError('error_message should only be set when status=failed')
        return v

    class Config:
        """Pydantic configuration."""
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }


class TaskDependency(BaseModel):
    """
    Represents a dependency relationship between tasks (directed edge in task DAG).

    Forms a Directed Acyclic Graph (DAG) - cycles not allowed.
    Per spec 004 requirement FR-010.
    """
    task_id: str = Field(..., description="Dependent task (must wait)")
    depends_on_task_id: str = Field(..., description="Prerequisite task (must complete first)")

    @field_validator('depends_on_task_id')
    @classmethod
    def no_self_dependency(cls, v: str, info) -> str:
        """Validate task cannot depend on itself."""
        if 'task_id' in info.data and v == info.data['task_id']:
            raise ValueError('Task cannot depend on itself')
        return v


# Priority level constants (convenience)
class TaskPriority:
    """Standard priority levels for tasks."""
    HIGH = 0
    MEDIUM = 50
    LOW = 100
