"""
MiMinions - A Python package for managing and interacting with AI agents
"""

try:
    from .agents import BaseAgent
    __all__ = ["BaseAgent"]
except ImportError:
    # In case optional dependencies are not installed
    __all__ = []

__version__ = "0.1.0"