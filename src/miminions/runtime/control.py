"""Utility functions for async operations, JSON handling, and agent execution."""
import asyncio
from typing import Dict, Any


class TaskRunner:
    """Async """
    def init_loop(self):
        """Initialize a new event loop."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)

    def terminate_loop(self):
        """Terminate the event loop and cancel all tasks."""
        self.loop.stop()
        self.loop.close()

    def run_async(self, async_func, *args, **kwargs):
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

    async def batch_run(self, async_funcs: Dict[str, set[Any]]) -> Dict[str, Any]:
        """Run a batch of async functions concurrently."""
        tasks = {}
        async with asyncio.TaskGroup() as tg:
            for name, (func, args) in async_funcs.items():
                tasks[name] = tg.create_task(func(*args))
        return {name: task.result() for name, task in tasks.items()}

    def run_batch(self, async_funcs: Dict[str, set[Any]]) -> Dict[str, Any]:
        """Run a batch of async functions in the event loop."""
        return self.run_async(self.batch_run, async_funcs)