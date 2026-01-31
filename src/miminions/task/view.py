"""
Docstring for src.miminions.task.view
In this module, it will generate high-level views like current task runtime summary
and single task detailed view.

In those views, we will aggregate information from multiple models like Task, AgentTask,
TaskInput, TaskOutput, etc., to provide a comprehensive overview include performance metrics,
status, history, and other relevant details.
"""
from typing import Any, Dict
from miminions.task.model import Task, AgentTask, TaskInput, TaskOutput