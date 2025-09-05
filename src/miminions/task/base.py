import uuid

class TaskStatus:
    INIT = "init"
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"

class BaseTask:
    def __init__(
            self,
            name: str, 
            description: str, 
            priority: str, 
            created_at: str, 
            updated_at: str,
            task_id: str = None,
            status: TaskStatus = TaskStatus.INIT,
        ):
        self.name = name
        self.description = description
        self.priority = priority
        self.task_id = task_id if task_id else str(uuid.uuid4())
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        
    def to_dict(self):
        return {
            "name": self.name,
            "description": self.description,
            "priority": self.priority,
            "status": self.status,
            "task_id": self.task_id,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass