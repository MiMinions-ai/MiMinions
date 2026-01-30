"""
Compatibility shim for Simple Agent

This module provides backward compatibility for imports from the old location.
The actual implementation has been moved to miminions.agent.simple_agent.

Usage:
    # Old import (still works)
    from miminions.agent.simple_agent import create_simple_agent
    
    # New recommended import
    from miminions.agent.simple_agent import create_simple_agent
"""

# Re-export everything from the new location for backward compatibility
from .simple_agent import Agent, create_simple_agent

__all__ = ["Agent", "create_simple_agent"]