"""
Data management module for MiMinions.

Provides local data management capabilities with master index, transaction logs,
and hash-based file storage.
"""

from .local import LocalDataManager

__all__ = ["LocalDataManager"]