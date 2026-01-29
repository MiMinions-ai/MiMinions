import asyncio
from logging import getLogger
from typing import Any, Dict

from unittest.mock import MagicMock

from miminions.task import TaskRuntime

DEFAULT_LOGGER = getLogger("miminions.task.examples")
DEFAULT_TASK_RUNTIME = TaskRuntime()

def run_single_task():
    DEFAULT_LOGGER.info("Running single task example...")
    pass

def run_task_chain():
    DEFAULT_LOGGER.info("Running task chain example...")
    pass

def run_multiple_tasks():
    DEFAULT_LOGGER.info("Running multiple tasks example...")
    pass

def run_task_petri_net():
    DEFAULT_LOGGER.info("Running task petri net example...")
    pass

async def run_single_task_async():
    DEFAULT_LOGGER.info("Running single task async example...")
    pass

async def run_task_chain_async():
    DEFAULT_LOGGER.info("Running task chain async example...")
    pass

async def run_multiple_tasks_async():
    DEFAULT_LOGGER.info("Running multiple tasks async example...")
    pass

async def run_task_petri_net_async():
    DEFAULT_LOGGER.info("Running task petri net async example...")
    pass

def main():
    DEFAULT_LOGGER.info("Running synchronous task examples...")
    run_single_task()
    run_task_chain()
    run_multiple_tasks()
    run_task_petri_net()

    DEFAULT_LOGGER.info("Running asynchronous task examples...")
    asyncio.run(run_single_task_async())
    asyncio.run(run_task_chain_async())
    asyncio.run(run_multiple_tasks_async())
    asyncio.run(run_task_petri_net_async())

if __name__ == "__main__":
    main()