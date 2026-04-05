"""Session distillation pipeline for hierarchical memory tiers."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from miminions.session.store import JsonlSessionStore

from .md_store import append_history, upsert_memory_section
from .sqlite import SQLiteMemory, get_global_memory_db_path


ALLOWED_GLOBAL_CATEGORIES = {"user_preference", "coding_standard", "achievement"}


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
    """Extract durable memory from session transcripts and promote by tier."""

    def __init__(
        self,
        llm_filter: Callable[..., dict[str, Any]],
        global_db_path: str | None = None,
        global_confidence_threshold: float = 0.85,
    ):
        if not callable(llm_filter):
            raise TypeError("llm_filter must be callable")
        self.llm_filter = llm_filter
        self.global_db_path = global_db_path or get_global_memory_db_path(create_dir=True)
        self.global_confidence_threshold = float(global_confidence_threshold)

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

    def _validate_extraction(self, payload: Any) -> tuple[dict[str, Any] | None, list[str]]:
        """Validate strict extraction schema required by distillation."""
        reasons: list[str] = []

        if not isinstance(payload, dict):
            return None, ["invalid_schema: payload must be an object"]

        required_keys = {"history_summary", "workspace_facts", "global_insights"}
        payload_keys = set(payload.keys())
        missing = sorted(required_keys - payload_keys)
        extra = sorted(payload_keys - required_keys)
        if missing:
            reasons.append(f"invalid_schema: missing keys {missing}")
        if extra:
            reasons.append(f"invalid_schema: unexpected keys {extra}")

        if "history_summary" in payload and not isinstance(payload.get("history_summary"), str):
            reasons.append("invalid_schema: history_summary must be string")

        workspace_facts = payload.get("workspace_facts")
        if "workspace_facts" in payload and not isinstance(workspace_facts, list):
            reasons.append("invalid_schema: workspace_facts must be list[str]")
        elif isinstance(workspace_facts, list):
            if any(not isinstance(item, str) for item in workspace_facts):
                reasons.append("invalid_schema: workspace_facts must contain only strings")

        global_insights = payload.get("global_insights")
        if "global_insights" in payload and not isinstance(global_insights, list):
            reasons.append("invalid_schema: global_insights must be list[object]")
        elif isinstance(global_insights, list):
            for idx, item in enumerate(global_insights):
                if not isinstance(item, dict):
                    reasons.append(f"invalid_schema: global_insights[{idx}] must be object")
                    continue
                expected_item_keys = {"text", "category", "confidence"}
                item_keys = set(item.keys())
                item_missing = sorted(expected_item_keys - item_keys)
                item_extra = sorted(item_keys - expected_item_keys)
                if item_missing:
                    reasons.append(
                        f"invalid_schema: global_insights[{idx}] missing keys {item_missing}"
                    )
                if item_extra:
                    reasons.append(
                        f"invalid_schema: global_insights[{idx}] unexpected keys {item_extra}"
                    )
                if "text" in item and not isinstance(item.get("text"), str):
                    reasons.append(f"invalid_schema: global_insights[{idx}].text must be string")
                if "category" in item and not isinstance(item.get("category"), str):
                    reasons.append(f"invalid_schema: global_insights[{idx}].category must be string")
                confidence = item.get("confidence")
                if "confidence" in item and not isinstance(confidence, (int, float)):
                    reasons.append(
                        f"invalid_schema: global_insights[{idx}].confidence must be number"
                    )

        if reasons:
            return None, reasons
        return payload, []

    def _normalize_lines(self, lines: list[str]) -> list[str]:
        """Normalize and dedupe text lines while preserving order."""
        seen: set[str] = set()
        normalized: list[str] = []
        for line in lines:
            clean = " ".join(line.split()).strip()
            if not clean:
                continue
            key = clean.casefold()
            if key in seen:
                continue
            seen.add(key)
            normalized.append(clean)
        return normalized

    def _is_durable_insight(self, text: str) -> bool:
        """Reject transient statements that should not be global memory."""
        lowered = text.casefold()
        transient_markers = (
            "today",
            "tomorrow",
            "this session",
            "for now",
            "next step",
            "todo",
            "temporary",
            "wip",
        )
        return not any(marker in lowered for marker in transient_markers)

    def _is_actionable_insight(self, text: str) -> bool:
        """Ensure insights are concrete enough to be useful later."""
        clean = text.strip()
        if len(clean) < 20:
            return False
        if clean.endswith("?"):
            return False
        return len(clean.split()) >= 4

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
        category: str,
        confidence: float,
    ) -> dict[str, Any]:
        return {
            "tier": 3,
            "category": category,
            "confidence": confidence,
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

        payload = self.llm_filter(
            transcript=transcript,
            workspace=workspace,
            root_path=str(root),
            session_id=session_id,
        )

        validated, reasons = self._validate_extraction(payload)
        if reasons:
            result.dropped_reasons.extend(reasons)
            return result
        assert validated is not None

        history_summary = validated["history_summary"].strip()
        workspace_facts = self._normalize_lines(validated["workspace_facts"])
        raw_global_insights: list[dict[str, Any]] = validated["global_insights"]

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

        accepted: list[dict[str, Any]] = []
        seen_insight_texts: set[str] = set()
        for insight in raw_global_insights:
            text = " ".join(insight["text"].split()).strip()
            category = insight["category"].strip()
            confidence = float(insight["confidence"])

            if not text:
                result.dropped_reasons.append("tier3_dropped: empty insight text")
                continue

            dedupe_key = text.casefold()
            if dedupe_key in seen_insight_texts:
                result.dropped_reasons.append(f"tier3_dropped: duplicate insight '{text}'")
                continue
            seen_insight_texts.add(dedupe_key)

            if category not in ALLOWED_GLOBAL_CATEGORIES:
                result.dropped_reasons.append(
                    f"tier3_dropped: unsupported category '{category}'"
                )
                continue

            if confidence < self.global_confidence_threshold:
                result.dropped_reasons.append(
                    f"tier3_dropped: confidence {confidence:.2f} below threshold"
                )
                continue

            if not self._is_durable_insight(text):
                result.dropped_reasons.append(
                    f"tier3_dropped: non-durable insight '{text}'"
                )
                continue

            if not self._is_actionable_insight(text):
                result.dropped_reasons.append(
                    f"tier3_dropped: non-actionable insight '{text}'"
                )
                continue

            accepted.append(
                {
                    "text": text,
                    "category": category,
                    "confidence": confidence,
                }
            )

        if accepted:
            sqlite_memory = SQLiteMemory(db_path=self.global_db_path)
            try:
                for insight in accepted:
                    metadata = self._build_tier3_metadata(
                        workspace=workspace,
                        session_id=session_id,
                        category=insight["category"],
                        confidence=insight["confidence"],
                    )
                    sqlite_memory.create(insight["text"], metadata=metadata)
                    result.promoted_counts["tier3"] += 1
                    result.global_insights.append({**insight, "metadata": metadata})
            finally:
                sqlite_memory.close()

        return result
