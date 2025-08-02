"""
Common CLI utilities for MiMinions

This module provides shared functionality for CLI commands to reduce duplication.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional

# Import common utilities
import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..'))
from miminions.core.common import config_manager, auth_decorator


class CLIConfigManager:
    """Centralized configuration management for CLI commands"""
    
    @staticmethod
    def load_agents() -> Dict[str, Any]:
        """Load agents from configuration"""
        return config_manager.load_json("agents.json", {})
    
    @staticmethod
    def save_agents(agents: Dict[str, Any]) -> None:
        """Save agents to configuration"""
        config_manager.save_json("agents.json", agents)
    
    @staticmethod
    def load_workspaces() -> Dict[str, Any]:
        """Load workspaces from configuration"""
        return config_manager.load_json("workspaces.json", {})
    
    @staticmethod
    def save_workspaces(workspaces: Dict[str, Any]) -> None:
        """Save workspaces to configuration"""
        config_manager.save_json("workspaces.json", workspaces)
    
    @staticmethod
    def load_tasks() -> Dict[str, Any]:
        """Load tasks from configuration"""
        return config_manager.load_json("tasks.json", {})
    
    @staticmethod
    def save_tasks(tasks: Dict[str, Any]) -> None:
        """Save tasks to configuration"""
        config_manager.save_json("tasks.json", tasks)
    
    @staticmethod
    def load_workflows() -> Dict[str, Any]:
        """Load workflows from configuration"""
        return config_manager.load_json("workflows.json", {})
    
    @staticmethod
    def save_workflows(workflows: Dict[str, Any]) -> None:
        """Save workflows to configuration"""
        config_manager.save_json("workflows.json", workflows)


class CLIUtils:
    """Common utilities for CLI commands"""
    
    @staticmethod
    def generate_id(name: str) -> str:
        """Generate a simple ID based on name"""
        return name.lower().replace(" ", "_").replace("-", "_")
    
    @staticmethod
    def validate_json(json_str: Optional[str]) -> Optional[Dict[str, Any]]:
        """Validate and parse JSON string"""
        if not json_str:
            return None
        
        try:
            return json.loads(json_str)
        except json.JSONDecodeError as e:
            raise ValueError(f"Invalid JSON: {e}")
    
    @staticmethod
    def format_timestamp() -> str:
        """Get current timestamp as string"""
        from datetime import datetime
        return datetime.now().isoformat()


# Global instances for reuse
cli_config = CLIConfigManager()
cli_utils = CLIUtils()
require_auth = auth_decorator.require_auth 