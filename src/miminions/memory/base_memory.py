# src/miminions/memory/base_memory.py

from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseMemory(ABC):
    """Abstract base class for vector-based memory systems."""

    @abstractmethod
    def create(self, text: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Add a new piece of knowledge and return its ID."""
        pass

    @abstractmethod
    def read(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        """Retrieve top-k similar knowledge entries."""
        pass

    @abstractmethod
    def update(self, id: str, new_text: str) -> bool:
        """Update a knowledge entry."""
        pass

    @abstractmethod
    def delete(self, id: str) -> bool:
        """Delete a knowledge entry."""
        pass

    @abstractmethod
    def get_by_id(self, id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a knowledge entry by its ID."""
        pass

    @abstractmethod
    def list_all(self) -> List[Dict[str, Any]]:
        """List all knowledge entries."""
        pass