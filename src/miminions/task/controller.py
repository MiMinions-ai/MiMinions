from enum import Enum
import asyncio
from typing import List, Optional

from miminions.task.base import AgentTask

class OrderBy(Enum):
    CREATED_AT = "created_at"
    UPDATED_AT = "updated_at"
    STATUS = "status"
    PRIORITY = "priority"





class TaskRunner:
    def __init__(
            self,
            tasks: Optional[List[AgentTask]] = None,
            continuous: bool = False,
            order_by: Optional[OrderBy] = OrderBy.PRIORITY,
        ):
        self.tasks = {task.task_id: task for task in tasks} if tasks else {}
        self.continuous = continuous
        self.order_by = order_by

    def add_task(self, task: AgentTask):
        self.tasks[task.task_id] = task

    def get_task(self, task_id: str):
        if task_id not in self.tasks:
            raise ValueError(f"Task with id {task_id} not found")
        return self.tasks[task_id]
    
    def filter_tasks(self, **kwargs):
        return [task for task in self.tasks.values() if all(getattr(task, k) == v for k, v in kwargs.items())]
    
    def update_task(self, task_id: str, **kwargs):
        self.tasks[task_id].update(**kwargs)

    def remove_task(self, task_id: str):
        del self.tasks[task_id]

    def run_task(self, task_id: str, continuous: bool = None, **kwargs):
        task = self.get_task(task_id)
        task.run(**kwargs)
        continuous = continuous if continuous is not None else self.continuous
        if continuous:
            next_task = self.get_task(task.next_task_id)
            self.run_task(next_task.task_id, continuous=continuous, **kwargs)
    
    def stop_task(self, task_id: str, **kwargs):
        task = self.get_task(task_id)
        task.stop(**kwargs)
    
    async def run_task_async(self, task_id: str, continuous: bool = None, **kwargs):
        task = self.get_task(task_id)
        result = await task.run_async(**kwargs)
        continuous = continuous if continuous is not None else self.continuous
        if continuous:
            next_task = self.get_task(task.next_task_id)
            result = await self.run_task_async(next_task.task_id, continuous=continuous, **kwargs)
        return result
    
    async def stop_task_async(self, task_id: str, **kwargs):
        task = self.get_task(task_id)
        task.stop_async(**kwargs)

    def run_tasks(self, order_by: Optional[OrderBy] = None, **kwargs):
        order_by = order_by if order_by is not None else self.order_by
        tasks = self.filter_tasks(**kwargs).copy()
        tasks.sort(key=lambda x: getattr(x, order_by.value))
        results = []
        for task in tasks:
            result = task.run(**kwargs)
            results.append(result)
        return results
    
    def stop_tasks(self, **kwargs):
        tasks = self.filter_tasks(**kwargs)
        for task in tasks:
            task.stop(**kwargs)

    def sort_tasks(self, tasks: List[AgentTask], order_by: Optional[OrderBy] = None):
        order_by = order_by
        tasks.sort(key=lambda x: getattr(x, order_by.value))
        return tasks
    
    async def run_tasks_async(self, order_by: Optional[OrderBy] = None, **kwargs):
        order_by = order_by if order_by is not None else self.order_by
        tasks = self.filter_tasks(**kwargs).copy()
        tasks.sort(key=lambda x: getattr(x, order_by.value))
        results = []
        async for task in asyncio.as_completed(tasks):
            result = await task.run_async(**kwargs)
            results.append(result)
        return results
    
    async def stop_tasks_async(self, **kwargs):
        tasks = self.filter_tasks(**kwargs)
        for task in tasks:
            task.stop_async(**kwargs)
    
    