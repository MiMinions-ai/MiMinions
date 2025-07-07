"""
MiMinions - A Python package for managing and interacting with AI agents
"""

from .main import greet

try:
    from .agents import BaseAgent
    __all__ = ["greet", "BaseAgent"]
except ImportError:
    # In case optional dependencies are not installed
    __all__ = ["greet"]

__version__ = "0.1.0"