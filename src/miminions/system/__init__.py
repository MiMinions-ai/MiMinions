"""
Data management module for MiMinions.

Provides local data management capabilities with master index, transaction logs,
and hash-based file storage.
"""

from .file import LocalDataManager

__all__ = ["LocalDataManager"]