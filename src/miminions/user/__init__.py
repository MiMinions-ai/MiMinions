"""
User module for MiMinions

This module provides user management capabilities including authentication,
validation, personalization, and data handling for the MiMinions system.
"""

try:
    from .model import User, UserProfile, UserPreferences
    from .controller import UserController
    from .auth import UserAuthenticator
    from .validator import UserValidator

    __version__ = "0.1.0"
    __all__ = [
        "User", 
        "UserProfile", 
        "UserPreferences", 
        "UserController", 
        "UserAuthenticator", 

    __version__ = "0.1.0"
    __all__ = [
        "User", 
        "UserProfile", 
        "UserPreferences"
    ]

except ImportError:
    # In case optional dependencies are not installed
    __all__ = []
