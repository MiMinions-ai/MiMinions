"""
User module for MiMinions

This module provides simple user management capabilities including basic CRUD operations
and API key management for the MiMinions system.
"""

try:
    from .model import User
    from .controller import UserController

    __version__ = "0.1.0"
    __all__ = [
        "User",
        "UserController"
    ]

except ImportError:
    # In case optional dependencies are not installed
    __all__ = []
