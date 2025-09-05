from enum import Enum
import uuid
from typing import Optional, Dict, Any
from datetime import datetime

from miminions.utility import FAKER
from miminions.agent.base_agent import BaseAgent

class TaskStatus(Enum):
    INIT = "init"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class TaskPriority(Enum):
    ON_DEMAND = "on_demand"
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
            states: Optional[list] = [],
            stop_condition: Optional[StopCondition] = None,
            success_critiera: Optional[str|list[str]] = [],
            priority: Optional[TaskPriority] = TaskPriority.ON_DEMAND,
            next_task_id: Optional[str|list[str]] = None,
        ):
        self.task_id = task_id if task_id else str(uuid.uuid4())
        self.name = name if name else FAKER.words(3)
        self.description = description
        self.priority = priority
        self.status = status
        self.states = states
        self.stop_condition = stop_condition
        self.success_critiera = success_critiera
        self.created_at = created_at if created_at else datetime.now().isoformat()
        self.updated_at = updated_at if updated_at else datetime.now().isoformat()
        self.next_task_id = next_task_id

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "task_id": self.task_id,
            "states": self.states,
            "stop_condition": self.stop_condition.value,
            "success_critiera": self.success_critiera,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "next_task_id": self.next_task_id
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]):
        return cls(**data)
    
    def update(self, **kwargs):
        for key, value in kwargs.items():
            setattr(self, key, value)
        self.updated_at = datetime.now().isoformat()
    
    def diff(self, other: object):
        if not isinstance(other, BaseTask):
            return NotImplemented
        return {key: value for key, value in self.to_dict().items() if value != other.to_dict()[key]}
    
    def __eq__(self, other: object):
        if not isinstance(other, BaseTask):
            return NotImplemented
        return self.to_dict() == other.to_dict()
    
    def __ne__(self, other: object):
        if not isinstance(other, BaseTask):
            return NotImplemented
        return self.to_dict() != other.to_dict()
    
    def __hash__(self):
        return hash(self.task_id)
    
    def __repr__(self):
        return f"BaseTask(task_id='{self.task_id}', name='{self.name}', status='{self.status.value}', priority='{self.priority.value}', created_at='{self.created_at}', updated_at='{self.updated_at}')"
    
    def __str__(self):
        return self.__repr__()
    
    def __iter__(self):
        return iter(self.to_dict().items())
    
    def __len__(self):
        return len(self.to_dict())
    
    def __getitem__(self, key: str):
        return self.to_dict()[key]
    
    def __setitem__(self, key: str, value: Any):
        setattr(self, key, value)
    
class AgentTask(BaseTask):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.agent = kwargs.get("agent") if kwargs.get("agent") else BaseAgent()

    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "priority": self.priority.value,
            "status": self.status.value,
            "task_id": self.task_id,
            "states": self.states,
            "stop_condition": self.stop_condition.value,
            "success_critiera": self.success_critiera,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
            "next_task_id": self.next_task_id,
            "agent": self.agent.to_dict()
        }
    
    def validate_success_critiera(self):
        pass
    
    def run(self, **kwargs):
        params = kwargs.copy()
        params["task_name"] = self.name
        params["task_description"] = self.description
        params["task_status"] = self.status.value
        params["task_states"] = self.states
        params["task_stop_condition"] = self.stop_condition.value
        params["task_success_critiera"] = self.success_critiera
        params["task_created_at"] = self.created_at
        params["task_updated_at"] = self.updated_at
        params["task_next_task_id"] = self.next_task_id

        result = self.agent.run(**params)
        if "state" in result:
            self.states.append(result.get("state", {}))
        
        self.updated_at = datetime.now().isoformat()
        self.status = result.get("status", self.status)
        return result
    
    def stop(self, **kwargs):
        return NotImplemented
    
    async def run_async(self, **kwargs):
        params = kwargs.copy()
        params["task_name"] = self.name
        params["task_description"] = self.description
        params["task_status"] = self.status.value
        params["task_states"] = self.states
        params["task_stop_condition"] = self.stop_condition.value
        params["task_success_critiera"] = self.success_critiera
        params["task_created_at"] = self.created_at
        params["task_updated_at"] = self.updated_at
        params["task_next_task_id"] = self.next_task_id
        return await self.agent.run_async(**params)
    
    async def stop_async(self, **kwargs):
        return NotImplemented
        