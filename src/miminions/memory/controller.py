from typing import Dict, Any, Optional, List
import itertools
import uuid
from datetime import datetime
from .base import (
    Memory,
    Message,
    Role
)

from .config import Config


class MemoryController:
    def __init__(self,**kwargs):
        self.config = Config(**kwargs)

    
    def create_message(self, raw_message: Dict[str, Any]) -> Message:
        """
        Create a message.
        """
        if not self.validate_message(raw_message):
            raise ValueError("Invalid message")
        return Message(
            id=str(uuid.uuid4()),
            content=raw_message["content"],
            role=Role(raw_message["role"]),
            created_at=datetime.now(),
            updated_at=datetime.now())

    def concatenate_memory(self, memories: List[Memory], user_id: str|None = None) -> str:
        """
        Concatenate a list of memories into a single memory.
        If user_id is provided, the memories will be concatenated into a single memory with the user_id.
        Else, the memories will be concatenated into a single memory with the first memory's user_id.
        """
        if not user_id:
            user_id = memories[0].user_id
        return Memory(
            id=str(uuid.uuid4()),
            user_id=user_id,
            messages=[*itertools.chain.from_iterable(m.messages for m in memories)],
            created_at=min(memory.created_at for memory in memories),
            updated_at=max(memory.updated_at for memory in memories),
            total_tokens=sum(memory.total_tokens for memory in memories)
        )
        

    def merge_memories(self, memories: List[Memory]) -> Memory:
        pass

    def assess_memory(self, memory: Memory) -> Memory:
        pass

    def compress_memory(self, memory: Memory) -> Memory:
        pass