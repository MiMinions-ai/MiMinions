"""
Common utilities and base classes for MiMinions

This module provides shared functionality to reduce code duplication across
the codebase.
"""

import json
from pathlib import Path
from typing import Any, Dict, List, Optional, Callable
from abc import ABC, abstractmethod
import functools


class ConfigManager:
    """Centralized configuration management to reduce duplication"""
    
    def __init__(self, config_dir: Optional[Path] = None):
        self.config_dir = config_dir or Path.home() / ".miminions"
        self.config_dir.mkdir(exist_ok=True)
    
    def get_config_file(self, filename: str) -> Path:
        """Get a configuration file path"""
        return self.config_dir / filename
    
    def load_json(self, filename: str, default: Dict[str, Any] = None) -> Dict[str, Any]:
        """Load JSON configuration file with default fallback"""
        config_file = self.get_config_file(filename)
        if not config_file.exists():
            return default or {}
        
        with open(config_file, "r") as f:
            return json.load(f)
    
    def save_json(self, filename: str, data: Dict[str, Any]) -> None:
        """Save data to JSON configuration file"""
        config_file = self.get_config_file(filename)
        with open(config_file, "w") as f:
            json.dump(data, config_file, indent=2)


class ToolManager:
    """Base tool management functionality to reduce duplication"""
    
    def __init__(self):
        self._tools: Dict[str, Callable] = {}
    
    def add_tool(self, name: str, tool_func: Callable) -> None:
        """Add a tool to the manager"""
        self._tools[name] = tool_func
    
    def remove_tool(self, name: str) -> None:
        """Remove a tool from the manager"""
        if name in self._tools:
            del self._tools[name]
    
    def get_tool(self, name: str) -> Optional[Callable]:
        """Get a tool by name"""
        return self._tools.get(name)
    
    def list_tools(self) -> List[str]:
        """List all available tool names"""
        return list(self._tools.keys())
    
    def has_tool(self, name: str) -> bool:
        """Check if a tool exists"""
        return name in self._tools
    
    def execute_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """Execute a tool by name"""
        tool = self.get_tool(tool_name)
        if tool is None:
            raise ValueError(f"Tool '{tool_name}' not found. Available tools: {self.list_tools()}")
        return tool(*args, **kwargs)


class AuthDecorator:
    """Centralized authentication decorator to reduce duplication"""
    
    def __init__(self, config_manager: ConfigManager):
        self.config_manager = config_manager
    
    def require_auth(self, allow_public: bool = True):
        """Decorator to require authentication or allow public access"""
        def decorator(f):
            @functools.wraps(f)
            def wrapper(*args, **kwargs):
                if not self._is_authenticated():
                    if allow_public and self._is_public_access_enabled():
                        # Show warning but allow access
                        import click
                        click.echo("⚠️  Running in public access mode. Sign in for full functionality.", err=True)
                    else:
                        # Require authentication
                        import click
                        click.echo("Please sign in first using 'miminions auth signin'", err=True)
                        return
                return f(*args, **kwargs)
            return wrapper
        return decorator
    
    def _is_authenticated(self) -> bool:
        """Check if user is authenticated"""
        auth_file = self.config_manager.get_config_file("auth.json")
        return auth_file.exists() and auth_file.stat().st_size > 0
    
    def _is_public_access_enabled(self) -> bool:
        """Check if public access mode is enabled"""
        config = self.config_manager.load_json("config.json", {"public_access": False})
        return config.get("public_access", False)


# Global instances for reuse
config_manager = ConfigManager()
auth_decorator = AuthDecorator(config_manager) 