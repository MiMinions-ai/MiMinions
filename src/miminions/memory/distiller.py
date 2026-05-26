"""Session distillation pipeline for hierarchical memory tiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from miminions.session.store import JsonlSessionStore

from .md_store import append_history, upsert_memory_section
from .sqlite import SQLiteMemory, get_global_memory_db_path


@dataclass
class DistillationResult:
    """Structured outcome for a single session distillation run."""

    history_summary: str = ""
    workspace_facts: list[str] = field(default_factory=list)
    global_insights: list[dict[str, Any]] = field(default_factory=list)
    promoted_counts: dict[str, int] = field(
        default_factory=lambda: {"tier1": 0, "tier2": 0, "tier3": 0}
    )
    dropped_reasons: list[str] = field(default_factory=list)


class MemoryDistiller:
    """Extract memory from session transcripts and promote by tier."""

    def __init__(
        self,
        llm_filter: Callable[..., dict[str, Any]],
        global_db_path: str | None = None,
    ):
        if not callable(llm_filter):
            raise TypeError("llm_filter must be callable")
        self.llm_filter = llm_filter
        self.global_db_path = global_db_path or get_global_memory_db_path(create_dir=True)

    def _compact_transcript(self, records: list[dict[str, Any]], max_messages: int = 80) -> str:
        """Build a compact transcript string for extraction."""
        lines: list[str] = []
        for record in records[-max_messages:]:
            role = str(record.get("role", "unknown")).strip() or "unknown"
            content = str(record.get("content", "")).strip()
            if not content:
                continue
            compact_content = " ".join(content.split())
            if len(compact_content) > 500:
                compact_content = compact_content[:497] + "..."
            lines.append(f"{role}: {compact_content}")
        return "\n".join(lines)

    def _as_list(self, value: Any) -> list[Any]:
        """Normalize optional list-like values from LLM output."""
        if value is None:
            return []
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            return [value]
        return []

    def _normalize_lines(self, lines: list[Any]) -> list[str]:
        """Normalize and dedupe text lines while preserving order."""
        seen: set[str] = set()
        normalized: list[str] = []
        for line in lines:
            clean = " ".join(str(line).split()).strip()
            if not clean:
                continue
            key = clean.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(clean)
        return normalized

    def _workspace_attr(self, workspace: Any, key: str, default: str = "") -> str:
        if isinstance(workspace, dict):
            value = workspace.get(key, default)
        else:
            value = getattr(workspace, key, default)
        return str(value or default)

    def _build_tier3_metadata(
        self,
        workspace: Any,
        session_id: str,
    ) -> dict[str, Any]:
        return {
            "tier": 3,
            "workspace_id": self._workspace_attr(workspace, "id"),
            "workspace_name": self._workspace_attr(workspace, "name"),
            "session_id": session_id,
            "source": "distiller",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }

    def distill_session(self, workspace: Any, root_path: str, session_id: str) -> DistillationResult:
        """Distill one session transcript into Tier 1/2/3 memory artifacts."""
        result = DistillationResult()

        root = Path(root_path)
        store = JsonlSessionStore(root)

        records = list(store.iter_messages(session_id) or [])
        if not records:
            result.dropped_reasons.append("empty_session: no transcript records")
            return result

        transcript = self._compact_transcript(records)
        if not transcript.strip():
            result.dropped_reasons.append("empty_session: transcript had no usable content")
            return result

        try:
            payload = self.llm_filter(
                transcript=transcript,
                workspace=workspace,
                root_path=str(root),
                session_id=session_id,
            )
        except Exception as exc:
            result.dropped_reasons.append(f"llm_filter_error: {exc}")
            return result

        if not isinstance(payload, dict):
            payload = {}

        history_summary = str(payload.get("history_summary", "")).strip()
        workspace_facts = self._normalize_lines(self._as_list(payload.get("workspace_facts")))

        global_insights: list[str] = []
        for insight in self._as_list(payload.get("global_insights")):
            if isinstance(insight, dict):
                text = str(insight.get("text", "")).strip()
            else:
                text = str(insight).strip()
            if text:
                global_insights.append(text)
        global_insights = self._normalize_lines(global_insights)

        if history_summary:
            append_history(root, history_summary)
            result.history_summary = history_summary
            result.promoted_counts["tier1"] += 1
        else:
            result.dropped_reasons.append("tier1_dropped: empty history_summary")

        if workspace_facts:
            upsert_memory_section(root, "Project Facts", workspace_facts)
            result.workspace_facts = workspace_facts
            result.promoted_counts["tier2"] += len(workspace_facts)

        if global_insights:
            try:
                sqlite_memory = SQLiteMemory(db_path=self.global_db_path)
                try:
                    for insight_text in global_insights:
                        metadata = self._build_tier3_metadata(
                            workspace=workspace,
                            session_id=session_id,
                        )
                        sqlite_memory.create(insight_text, metadata=metadata)
                        result.promoted_counts["tier3"] += 1
                        result.global_insights.append(
                            {
                                "text": insight_text,
                                "metadata": metadata,
                            }
                        )
                finally:
                    sqlite_memory.close()
            except Exception as exc:
                result.dropped_reasons.append(f"tier3_unavailable: {exc}")

        return result

