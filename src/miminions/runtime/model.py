"""Module for runtime models."""
from uuid import uuid1
from enum import Enum
from typing import Any, Dict, List

from pydantic import BaseModel, Field
from pydantic_ai import Agent

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

class AgentTask(Task):
    """Model representing a task assigned to an agent."""
    agent: Agent = Field(..., description="Agent assigned to the task")
    args: List[Any] = Field(default=[], description="Arguments for the task execution")
    kwargs: Dict[str, Any] = Field(default_factory=dict, description="Keyword arguments for the task execution")