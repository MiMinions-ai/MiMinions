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
        self.tasks = []
        self.status = TaskStatus.INITIALIZED
        self.last_update = datetime.now()

    def add_task(self, task: AgentTask):
        """Add a new task to the runner."""
        self.tasks.append(task)
        self.last_update = datetime.now()
        self.status = TaskStatus.IDLE

    def get_tasks(self):
        """Get the list of tasks."""
        return self.tasks

    def filter_tasks(self, attribute: str, value: Any):
        """Filter tasks based on a specific attribute and value."""
        return [task for task in self.tasks if getattr(task, attribute) == value]

    def update_task_status(self, task_id: str, new_status: TaskStatus):
        """Update the status of a specific task."""
        for task in self.tasks:
            if task.id == task_id:
                task.status = new_status.value
                self.last_update = datetime.now()
                break

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

    async def run(self, async_funcs: Dict[str, set[Any]]) -> Dict[str, Any]:
        """Run a batch of async functions concurrently."""
        tasks = {}
        async with asyncio.TaskGroup() as tg:
            for name, (func, args) in async_funcs.items():
                tasks[name] = tg.create_task(func(*args))
        return {name: task.result() for name, task in tasks.items()}

    def run_sync(self, async_funcs: Dict[str, set[Any]]) -> Dict[str, Any]:
        """Run a batch of async functions in the event loop."""
        return self.run_async_func(self.run, async_funcs)