"""Module for runtime models."""
from uuid import uuid1
from enum import Enum
from typing import Any, Dict, List, Optional
from dataclasses import field,dataclass
from datetime import datetime

from pydantic_ai import Agent, AgentRunResult

from miminions.utils import (
    generate_random_name,
    generate_random_description,
)

# Task models
class TaskStatus(Enum):
    """Enumeration of possible task status values."""
    PENDING = "pending"  # Task created, waiting to be initialized
    INITIALIZED = "initialized"  # Task initialized and ready
    IDLE = "idle"  # Task ready to execute
    RUNNING = "running"  # Task currently executing
    IN_PROGRESS = "in_progress"  # Task in progress (alias for CLI compatibility)
    PAUSED = "paused"  # Task execution paused
    COMPLETED = "completed"  # Task completed successfully
    FAILED = "failed"  # Task failed with error
    CANCELLED = "cancelled"  # Task cancelled by user

class TaskPriority(Enum):
    """Enumeration of task priority levels."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class Task:
    """Model representing a task in the runtime environment."""
    id: str = field(
        default_factory=lambda: str(uuid1()),
        metadata={"description":"Unique identifier for the task"}
    )
    name: str = field(
        default_factory=generate_random_name, 
        metadata={"description":"Name of the task"}
    )
    description: str = field(
        default_factory=generate_random_description, 
        metadata={"description":"Detailed description of the task"}
    )
    status: TaskStatus = field(
        default=TaskStatus.PENDING, 
        metadata={"description":"Current status of the task"}
    )
    priority: TaskPriority = field(
        default=TaskPriority.MEDIUM, 
        metadata={"description":"Priority level of the task"}
    )
    start_time: Optional[datetime] = field(
        default=None, 
        metadata={"description":"Start time of the task"}
    )
    end_time: Optional[datetime] = field(
        default=None, 
        metadata={"description":"End time of the task"}
    )

@dataclass
class AgentTask(Task):
    """Model representing a task assigned to an agent."""
    agent: Agent = field(
        default=None, 
        metadata={"description":"Agent assigned to the task"}
    )
    args: List[Any] = field(
        default_factory=list, 
        metadata={"description":"Arguments for the task execution"}
    )
    max_turns: int = field(
        default=5, 
        metadata={"description":"Maximum number of turns for the agent to complete the task"}
    )
    kwargs: Dict[str, Any] = field(
        default_factory=dict, 
        metadata={"description":"Keyword arguments for the task execution"}
    )
    call_back: Optional[callable] = field(
        default=None, 
        metadata={"description":"Callback function after task completion"}
    )
    result: AgentRunResult = field(
        default=None, 
        metadata={"description":"Result of the task execution"}
    )

@dataclass
class TaskInput:
    """Model representing input parameters for a task."""
    params: Dict[str, Any] = field(
        default_factory=dict, 
        metadata={"description":"Input parameters for the task"}
    )

@dataclass
class TaskOutput:
    """Model representing output results of a task."""
    results: Dict[str, Any] = field(
        default_factory=dict,
        metadata={"description":"Output results of the task"}
    )