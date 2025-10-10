"""
MiMinions Agents Module

This module provides the base agent functionality for the MiMinions framework.
"""

from .base import Agent as BaseAgent
from .simple_agent import Agent

__all__ = ["BaseAgent", "Agent"]
