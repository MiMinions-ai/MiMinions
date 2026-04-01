import asyncio
import logging
from typing import Any, Dict

from unittest.mock import MagicMock

from miminions.task import TaskRuntime, AgentTask, TaskStatus

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

DEFAULT_LOGGER = logging.getLogger("miminions.task.examples")
DEFAULT_TASK_RUNTIME = TaskRuntime()

def run_single_task():
    """
    Example of running a single task with a mock agent synchronously.
    Demonstrates:
    - Creating a mock agent
    - Creating an AgentTask
    - Adding task to runtime
    - Running the task synchronously
    - Checking task status and result
    """
    DEFAULT_LOGGER.info("Running single task example...")
    
    # Create a mock agent with async run method
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.data = "Task completed successfully!"
    
    # Mock the run method to return the result
    async def mock_run(*args, **kwargs):
        return mock_result
    
    mock_agent.run = mock_run
    
    # Create an AgentTask
    task = AgentTask()
    task.name = "mock_task"
    task.description = "A simple mock task to demonstrate single task execution"
    task.agent = mock_agent
    task.args = ["Calculate the meaning of life"]
    task.kwargs = {}
    task.max_turns = 3
    task.status = TaskStatus.IDLE
    
    DEFAULT_LOGGER.info(f"Created task: {task.name} (ID: {task.id})")
    
    # Add task to runtime
    runtime = TaskRuntime()
    runtime.add_task(task)
    
    DEFAULT_LOGGER.info(f"Task added to runtime. Runtime status: {runtime.status}")
    
    # Run the task synchronously
    DEFAULT_LOGGER.info("Executing task...")
    results = runtime.run_sync()
    
    # Check results
    DEFAULT_LOGGER.info(f"Task execution completed!")
    DEFAULT_LOGGER.info(f"Task status: {task.status}")
    DEFAULT_LOGGER.info(f"Task result: {task.result.data if task.result else 'No result'}")
    DEFAULT_LOGGER.info(f"Results summary: {results}")
    
    return results

# def run_task_chain():
#     DEFAULT_LOGGER.info("Running task chain example...")
#     pass

def run_multiple_tasks():
    DEFAULT_LOGGER.info("Running multiple tasks example...")
    pass

# def run_task_petri_net():
#     DEFAULT_LOGGER.info("Running task petri net example...")
#     pass

async def run_single_task_async():
    """
    Example of running a single task with a mock agent asynchronously.
    Demonstrates:
    - Creating a mock agent
    - Creating an AgentTask
    - Adding task to runtime
    - Running the task asynchronously
    - Checking task status and result
    """
    DEFAULT_LOGGER.info("Running single task async example...")
    
    # Create a mock agent with async run method
    mock_agent = MagicMock()
    mock_result = MagicMock()
    mock_result.data = "Async task completed successfully!"
    
    # Mock the run method to return the result after a delay
    async def mock_run(*args, **kwargs):
        await asyncio.sleep(0.5)  # Simulate some processing time
        return mock_result
    
    mock_agent.run = mock_run
    
    # Create an AgentTask
    task = AgentTask()
    task.name = "async_mock_task"
    task.description = "A simple async mock task to demonstrate single task execution"
    task.agent = mock_agent
    task.args = ["What is the purpose of async programming?"]
    task.kwargs = {}
    task.max_turns = 3
    task.status = TaskStatus.IDLE
    
    DEFAULT_LOGGER.info(f"Created async task: {task.name} (ID: {task.id})")
    
    # Add task to runtime
    runtime = TaskRuntime()
    runtime.add_task(task)
    
    DEFAULT_LOGGER.info(f"Task added to runtime. Runtime status: {runtime.status}")
    
    # Run the task asynchronously
    DEFAULT_LOGGER.info("Executing async task...")
    results = await runtime.run()
    
    # Check results
    DEFAULT_LOGGER.info(f"Async task execution completed!")
    DEFAULT_LOGGER.info(f"Task status: {task.status}")
    DEFAULT_LOGGER.info(f"Task result: {task.result.data if task.result else 'No result'}")
    DEFAULT_LOGGER.info(f"Results summary: {results}")
    
    return results

# async def run_task_chain_async():
#     DEFAULT_LOGGER.info("Running task chain async example...")
#     pass

async def run_multiple_tasks_async():
    DEFAULT_LOGGER.info("Running multiple tasks async example...")
    pass

# async def run_task_petri_net_async():
#     DEFAULT_LOGGER.info("Running task petri net async example...")
#     pass

def main():
    DEFAULT_LOGGER.info("Running synchronous task examples...")
    run_single_task()
    # run_task_chain()
    run_multiple_tasks()
    # run_task_petri_net()

    DEFAULT_LOGGER.info("\nRunning asynchronous task examples...")
    asyncio.run(run_single_task_async())
    # asyncio.run(run_task_chain_async())
    asyncio.run(run_multiple_tasks_async())
    # asyncio.run(run_task_petri_net_async())

if __name__ == "__main__":
    main()