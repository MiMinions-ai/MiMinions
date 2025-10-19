from enum import Enum
from uuid import uuid4
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

from ..utility import ENCODER

class Role(Enum):
    USER = "user"
    ASSISTANT = "assistant"
    SYSTEM = "system"

@dataclass
class Message:
    id: str = field(default_factory=lambda: str(uuid4()))
    content: str = field(default="")
    content_tokens: int = field(default=0)
    role: Role = field(default_factory=lambda: Role.USER)
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: datetime = field(default_factory=lambda: datetime.now())

    @classmethod
    def count_content_tokens(cls, content: str) -> int:
        return len(ENCODER.encode(content))

    def update_content_tokens(self) -> None:
        self.content_tokens = self.count_content_tokens(self.content)

    def to_chat_message(self) -> Dict[str, Any]:
        return {
            "content": self.content,
            "role": self.role.value,
        }

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "content": self.content,
            "content_tokens": self.content_tokens,
            "role": self.role.value,
            "created_at": self.created_at,
            "updated_at": self.updated_at
        }

    @classmethod
    def from_chat_message(cls, chat_message: dict) -> 'Message':
        if not cls.validate_chat_message(chat_message):
            raise ValueError("Invalid chat message")
        return Message(
            id=str(uuid4()),
            content=chat_message["content"],
            content_tokens=cls.count_content_tokens(chat_message["content"]),
            role=Role(chat_message["role"]),
            created_at=datetime.now(),
            updated_at=datetime.now())

    @classmethod
    def validate_chat_message(cls, chat_message: dict) -> bool:
        if not isinstance(chat_message, dict):
            return False
        if "content" not in chat_message:
            return False
        if "role" not in chat_message:
            return False
        if chat_message["role"] not in Role.__members__:
            return False
        return True

@dataclass
class Memory:
    id: str = field(default_factory=lambda: str(uuid4()))
    user_id: str|None = field(default=None)
    messages: List[Message] = field(default= [])
    total_tokens: int = field(default=0)
    created_at: datetime = field(default_factory=lambda: datetime.now())
    updated_at: datetime = field(default_factory=lambda: datetime.now())

    def __init__(self,**kwargs):
        self.id = kwargs.get("id")
        self.user_id = kwargs.get("user_id")
        self.messages = kwargs.get("messages")
        self.created_at = datetime.now()
        self.updated_at = datetime.now()


    def add_chat_message(self, chat_message: dict) -> None:
        if not Message.validate_chat_message(chat_message):
            raise ValueError("Invalid chat message")
        message = Message.from_chat_message(chat_message)
        self.messages.append(message)
        self.total_tokens += message.content_tokens
        self.updated_at = datetime.now()


    def to_chat_messages(self) -> List[Dict[str, Any]]:
        return [message.to_chat_message() for message in self.messages]


    def filter_messages(self, **kwargs) -> List[Message]:
        if not self.validate_filter(**kwargs):
            raise ValueError("Invalid filter")
        return [message for message in self.messages if all(getattr(message, key) == value for key, value in kwargs.items())]


    def validate_filter(self, **kwargs) -> bool:
        for key, value in kwargs.items():
            if not key in Message.__dataclass_fields__:
                return False
            if key == "role":
                if value not in Role.__members__:
                    return False
        return True

    def from_chat_messages(self, chat_messages: List[Dict[str, Any]], user_id: str|None = None) -> 'Memory':
        self.messages = []
        for chat_message in chat_messages:
            self.messages.append(Message.from_chat_message(chat_message))

        self.id = str(uuid4())
        self.user_id = user_id
        self.created_at = min(message.created_at for message in self.messages)
        self.updated_at = datetime.now()
        self.total_tokens = sum(message.content_tokens for message in self.messages)
