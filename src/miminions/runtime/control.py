"""Utility functions for async operations, JSON handling, and agent execution."""
import asyncio
from typing import Dict, Any
from datetime import datetime

from miminions.runtime.model import (
    AgentTask,
    TaskStatus
)



class TaskRuntime:
    """Agentic Task Runner for managing and executing async tasks."""
    def __init__(self):
        self.loop = None
        self.tasks: Dict[str, AgentTask] = {}
        self.status = TaskStatus.INITIALIZED
        self.last_update = datetime.now()

    def add_task(self, task: AgentTask):
        """Add a new task to the runner."""
        self.tasks[task.id] = task
        self.last_update = datetime.now()
        self.status = TaskStatus.IDLE

    def get_tasks(self):
        """Get the list of tasks."""
        return self.tasks

    def filter_tasks(self, attribute: str, value: Any):
        """Filter tasks based on a specific attribute and value."""
        return [task for task in self.tasks if getattr(task, attribute) == value]

    def update_task(self, task_id: str, **task_attributes):
        """Update the status of a specific task."""
        if not self.tasks:
            raise ValueError("No tasks available to update.")
        if task_id not in self.tasks:
            raise ValueError(f"Task with id {task_id} not found.")
        task = self.tasks[task_id]
        for attr, val in task_attributes.items():
            setattr(task, attr, val)
        self.last_update = datetime.now()

    def clear_tasks(self):
        """Clear all tasks from the runner."""
        self.tasks.clear()
        self.last_update = datetime.now()
        self.status = TaskStatus.IDLE

    def init_loop(self):
        """Initialize a new event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def terminate_loop(self):
        """Terminate the event loop and cancel all tasks."""
        self.loop.stop()
        self.loop.close()

    def run_async_func(self, async_func, *args, **kwargs):
        """Run an async function in the event loop."""        
        try:
            self.init_loop()
            return self.loop.run_until_complete(async_func(*args, **kwargs))
        except:
            # Close the existing loop if open
            if self.loop is not None:
                self.terminate_loop()
            # Create a new loop for retry
            self.init_loop()
            return self.loop.run_until_complete(async_func(*args, **kwargs))
        finally:
            self.terminate_loop()

    async def run(self) -> Dict[str, Any]:
        """
        Run all tasks concurrently and return their statuses and results.

        Returns:
            Dict[str, Any]: A dictionary with task names as keys and their status and result.
        """
        tasks = {}
        async with asyncio.TaskGroup() as tg:
            for name, task in self.tasks.items():
                tasks[name] = tg.create_task(
                    coro=task.agent.run(*task.args, **task.kwargs),
                    name=name
                )
                task.status = TaskStatus.RUNNING
        
        for name, task in tasks.items():
            try:
                self.tasks[name].result = task.result()
                self.tasks[name].status = TaskStatus.COMPLETED
            except Exception as e:
                self.tasks[name].status = TaskStatus.FAILED

        return {
            name: {
                "status": task.status,
                "result": task.result
            } for name, task in self.tasks.items()
        }

    def run_sync(self) -> Dict[str, Any]:
        """Run a batch of async functions in the event loop."""
        return self.run_async_func(self.run)

    async def get_task_status(self, task_id: str=None) -> TaskStatus:
        """Get the status of a specific task asynchronously."""
        if not self.tasks:
            raise ValueError("No tasks available.")
        if not task_id:
            return {task.id: task.status for task in self.tasks.values()}
        if task_id not in self.tasks:
            raise ValueError(f"Task with id {task_id} not found.")
        return self.tasks[task_id].status
