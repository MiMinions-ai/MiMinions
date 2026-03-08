"""Session-scoped conversation state management.

Sessions store a list of message dicts with channel source and other DTO
attributes.  Persistence uses JSONL format with a configurable storage
location.
"""

import json
import logging
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class SessionMessage:
    """DTO for a single message within a session."""

    role: str
    content: str
    channel: str = ""
    sender_id: str | None = None
    chat_id: str | None = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    media: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict."""
        return {
            "role": self.role,
            "content": self.content,
            "channel": self.channel,
            "sender_id": self.sender_id,
            "chat_id": self.chat_id,
            "timestamp": self.timestamp,
            "media": self.media,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SessionMessage":
        """Deserialize from a plain dict."""
        return cls(
            role=data.get("role", ""),
            content=data.get("content", ""),
            channel=data.get("channel", ""),
            sender_id=data.get("sender_id"),
            chat_id=data.get("chat_id"),
            timestamp=data.get("timestamp", ""),
            media=data.get("media", []),
            metadata=data.get("metadata", {}),
        )


@dataclass
class Session:
    """
    A conversation session.

    Stores messages as append-only list of dicts (each dict contains channel
    source, sender, and other DTO attributes) in JSONL format for persistence.
    """

    key: str  # e.g. channel:chat_id
    messages: list[dict[str, Any]] = field(default_factory=list)
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def add_message(
        self,
        role: str,
        content: str,
        channel: str = "",
        sender_id: str | None = None,
        chat_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        """Add a message to the session."""
        msg = SessionMessage(
            role=role,
            content=content,
            channel=channel,
            sender_id=sender_id,
            chat_id=chat_id,
            **kwargs,
        )
        self.messages.append(msg.to_dict())
        self.updated_at = datetime.now()

    def get_history(self, max_messages: int = 500) -> list[dict[str, Any]]:
        """Return recent messages, aligned to a user turn boundary."""
        sliced = self.messages[-max_messages:]
        # Drop leading non-user messages to avoid orphaned context
        for i, m in enumerate(sliced):
            if m.get("role") == "user":
                sliced = sliced[i:]
                break
        return sliced

    def clear(self) -> None:
        """Clear all messages and reset the session."""
        self.messages = []
        self.updated_at = datetime.now()


def _safe_filename(key: str) -> str:
    """Convert a session key to a filesystem-safe filename."""
    return key.replace(":", "_").replace("/", "_").replace("\\", "_")


class SessionManager:
    """
    Manages conversation sessions with a configurable persistence location.

    Sessions are stored as JSONL files.  Each file starts with a metadata
    line followed by one JSON object per message.
    """

    def __init__(
        self,
        storage_path: Path | str,
        ttl_seconds: float = 3600,
    ) -> None:
        self.storage_path = Path(storage_path)
        self.storage_path.mkdir(parents=True, exist_ok=True)
        self._cache: dict[str, tuple[Session, float]] = {}
        self._ttl_seconds = ttl_seconds

    def _get_session_path(self, key: str) -> Path:
        """Get the file path for a session."""
        return self.storage_path / f"{_safe_filename(key)}.jsonl"

    def _evict_expired(self) -> None:
        """Remove cache entries that have exceeded the TTL."""
        now = time.monotonic()
        expired = [
            k for k, (_, ts) in self._cache.items()
            if now - ts > self._ttl_seconds
        ]
        for k in expired:
            del self._cache[k]

    def get_or_create(self, key: str) -> Session:
        """Get an existing session or create a new one."""
        self._evict_expired()
        if key in self._cache:
            session, _ = self._cache[key]
            self._cache[key] = (session, time.monotonic())
            return session

        session = self._load(key)
        if session is None:
            session = Session(key=key)

        self._cache[key] = (session, time.monotonic())
        return session

    def _load(self, key: str) -> Session | None:
        """Load a session from disk."""
        path = self._get_session_path(key)
        if not path.exists():
            return None

        try:
            messages: list[dict[str, Any]] = []
            metadata: dict[str, Any] = {}
            created_at: datetime | None = None

            with open(path, encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue

                    data = json.loads(line)

                    if data.get("_type") == "metadata":
                        metadata = data.get("metadata", {})
                        if data.get("created_at"):
                            created_at = datetime.fromisoformat(data["created_at"])
                    else:
                        messages.append(data)

            return Session(
                key=key,
                messages=messages,
                created_at=created_at or datetime.now(),
                metadata=metadata,
            )
        except Exception:
            logger.exception("Failed to load session %s", key)
            return None

    def save(self, session: Session) -> None:
        """Save a session to disk as JSONL."""
        path = self._get_session_path(session.key)

        with open(path, "w", encoding="utf-8") as f:
            metadata_line = {
                "_type": "metadata",
                "key": session.key,
                "created_at": session.created_at.isoformat(),
                "updated_at": session.updated_at.isoformat(),
                "metadata": session.metadata,
            }
            f.write(json.dumps(metadata_line, ensure_ascii=False) + "\n")
            for msg in session.messages:
                f.write(json.dumps(msg, ensure_ascii=False) + "\n")

        self._cache[session.key] = (session, time.monotonic())

    def invalidate(self, key: str) -> None:
        """Remove a session from the in-memory cache."""
        self._cache.pop(key, None)

    def delete(self, key: str) -> bool:
        """Delete a session from disk and cache."""
        self._cache.pop(key, None)
        path = self._get_session_path(key)
        if path.exists():
            path.unlink()
            return True
        return False

    def list_sessions(self) -> list[dict[str, Any]]:
        """List all persisted sessions with their metadata."""
        sessions: list[dict[str, Any]] = []

        for path in self.storage_path.glob("*.jsonl"):
            try:
                with open(path, encoding="utf-8") as f:
                    first_line = f.readline().strip()
                    if first_line:
                        data = json.loads(first_line)
                        if data.get("_type") == "metadata":
                            sessions.append({
                                "key": data.get("key", path.stem),
                                "created_at": data.get("created_at"),
                                "updated_at": data.get("updated_at"),
                                "path": str(path),
                            })
            except Exception:
                continue

        return sorted(
            sessions,
            key=lambda x: x.get("updated_at", ""),
            reverse=True,
        )
