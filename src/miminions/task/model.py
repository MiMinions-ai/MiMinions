"""Module for runtime models."""
from uuid import uuid1
from enum import Enum
from typing import Any, Dict, List, Optional
from datetime import datetime

from pydantic import BaseModel, Field
from pydantic_ai import Agent, AgentRunResult

from miminions.utils import (
    generate_random_name,
    generate_random_description,
)

# Task models
class TaskStatus(Enum):
    INITIALIZED = "initialized"
    IDLE = "idle"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"

class Task(BaseModel):
    """Model representing a task in the runtime environment."""
    id: str = Field(default_factory=lambda: str(uuid1()),
        description="Unique identifier for the task")
    name: str = Field(default_factory=generate_random_name, description="Name of the task")
    description: str = Field(default_factory=generate_random_description, description="Detailed description of the task")
    status: str = Field(..., description="Current status of the task")
    priority: int = Field(..., description="Priority level of the task")
    start_time: Optional[datetime] = Field(default=None, description="Start time of the task")
    end_time: Optional[datetime] = Field(default=None, description="End time of the task")

class AgentTask(Task):
    """Model representing a task assigned to an agent."""
    agent: Agent = Field(..., description="Agent assigned to the task")
    args: List[Any] = Field(default=[], description="Arguments for the task execution")
    max_turns: int = Field(default=5, description="Maximum number of turns for the agent to complete the task")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Keyword arguments for the task execution")
    call_back: Optional[callable] = Field(default=None, description="Callback function after task completion")
    result: AgentRunResult = Field(default=None, description="Result of the task execution")

class TaskInput(BaseModel):
    """Model representing input parameters for a task."""
    params: Dict[str, Any] = Field(..., description="Input parameters for the task")

class TaskOutput(BaseModel):
    """Model representing output results of a task."""
    results: Dict[str, Any] = Field(..., description="Output results of the task")
