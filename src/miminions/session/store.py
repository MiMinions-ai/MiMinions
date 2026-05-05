from __future__ import annotations

import json
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Iterator, Optional

from miminions.workspace_fs.layout import WorkspaceLayout

JsonDict = Dict[str, Any]

def create_session_id() -> str:
    """Create a readable unique session id.

    Format: YYYYMMDDTHHMMSSffffffZ_<8-char-uuid>
    """
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    suffix = uuid.uuid4().hex[:8]
    return f"{timestamp}_{suffix}"


class JsonlSessionStore:
    """Append-only JSONL session store rooted at a workspace folder.

    Each session is stored at:
        <workspace_root>/sessions/<session_id>.jsonl
    """

    def __init__(self, root_path: str | Path):
        self.layout = WorkspaceLayout.from_root(root_path)
        self.layout.sessions_dir.mkdir(parents=True, exist_ok=True)

    def path_for(self, session_id: str) -> Path:
        """Return the file path for a session id."""
        safe_session_id = session_id.strip()
        if not safe_session_id:
            raise ValueError("session_id cannot be empty")
        if Path(safe_session_id).name != safe_session_id:
            raise ValueError("session_id must not contain path separators")
        return self.layout.sessions_dir / f"{safe_session_id}.jsonl"

    def create_session_id(self) -> str:
        """Create a new session id."""
        return create_session_id()

    def append(
        self,
        session_id: str,
        role: str,
        content: str,
        meta: Optional[JsonDict] = None,
    ) -> JsonDict:
        """Append one message to a session log and return the record written."""
        role = role.strip()
        if not role:
            raise ValueError("role cannot be empty")
        if content is None:
            raise ValueError("content cannot be None")

        record: JsonDict = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "session_id": session_id,
            "role": role,
            "content": content,
        }
        if meta is not None:
            record["meta"] = meta

        session_path = self.path_for(session_id)
        session_path.parent.mkdir(parents=True, exist_ok=True)
        session_path.touch(exist_ok=True)

        with session_path.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record, ensure_ascii=False) + "\n")

        return record

    def iter_messages(self, session_id: str) -> Iterator[JsonDict]:
        """Yield session records in the order they were written."""
        session_path = self.path_for(session_id)
        if not session_path.exists():
            return

        with session_path.open("r", encoding="utf-8") as f:
            for line_number, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue
                try:
                    yield json.loads(line)
                except json.JSONDecodeError as exc:
                    raise ValueError(
                        f"Invalid JSONL in session file {session_path} at line {line_number}"
                    ) from exc

    def load_as_pydantic_messages(self, session_id: str) -> list:
        """Load a saved session as pydantic_ai ``ModelMessage`` objects.

        Converts each JSONL record into the pydantic_ai message type that
        ``Agent.run(message_history=...)`` expects:

        - ``role == "user"``      → ``ModelRequest(parts=[UserPromptPart(...)])``
        - ``role == "assistant"`` → ``ModelResponse(parts=[TextPart(...)])``
        - Any other role is silently skipped (tool calls are not re-injected).

        Returns an empty list if the session file does not exist or is empty,
        so callers never need to guard against ``None``.
        """
        from pydantic_ai.messages import (
            ModelRequest,
            ModelResponse,
            UserPromptPart,
            TextPart,
        )

        messages: list = []
        for record in self.iter_messages(session_id):
            role = record.get("role", "")
            content = record.get("content", "")
            if not content:
                continue
            if role == "user":
                messages.append(
                    ModelRequest(parts=[UserPromptPart(content=content)])
                )
            elif role == "assistant":
                messages.append(
                    ModelResponse(
                        parts=[TextPart(content=content)],
                        model_name="openrouter",
                    )
                )
        return messages