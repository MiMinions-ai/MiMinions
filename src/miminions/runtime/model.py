"""Module for runtime models."""
from uuid import uuid1
from enum import Enum

from pydantic import BaseModel, Field

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
    agent_id: str = Field(..., description="Identifier of the agent assigned to the task")
    deadline: str = Field(..., description="Deadline for task completion")

