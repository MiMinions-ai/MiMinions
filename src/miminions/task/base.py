from enum import Enum
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from miminions.utility import FAKER

class TaskStatus(Enum):
    INIT = "init"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskPriority(Enum):
    NEXT_UP = "next_up"
    ON_DEMAND = "on_demand"
    SCHEDULED = "scheduled"
    RESERVED = "reserved"

class StopCondition(Enum):
    TIMEOUT = "timeout"
    ERROR = "error"
    MANUAL = "manual"
    COMPLETED = "completed"
    FAILED = "failed"

class BaseTask:
    def __init__(
            self,
            created_at: Optional[str] = None, 
            updated_at: Optional[str] = None,
            name: Optional[str] = None, 
            task_id: Optional[str] = None,
            status: TaskStatus = TaskStatus.INIT,
            description: Optional[str] = None, 
            prior_state: Optional[dict] = None,
            stop_condition: Optional[StopCondition] = None,
            priority: Optional[TaskPriority] = TaskPriority.NEXT_UP, 
        ):
        self.task_id = task_id if task_id else str(uuid.uuid4())
        self.name = name if name else FAKER.words(3)
        self.description = description
        self.priority = priority
        self.status = status
        self.prior_state = prior_state
        self.stop_condition = stop_condition
        self.created_at = created_at if created_at else datetime.now().isoformat()
        self.updated_at = updated_at if updated_at else datetime.now().isoformat()

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "task_id": self.task_id,
            "prior_state": self.prior_state,
            "stop_condition": self.stop_condition.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)