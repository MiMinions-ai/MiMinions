"""Pressure-triggered compaction of the MEMORY.md stable-fact tier."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from .budget import CompactionOutcome, MemoryBudgets, check_pressure, count_tokens, record_state
from .md_store import read_memory, write_memory

logger = logging.getLogger(__name__)

_ARCHIVE_HEADING = "Archived Facts"


def _parse_facts(content: str) -> list[tuple[str, str]]:
    """Return (section_heading, fact_text) for each top-level bullet in MEMORY.md.

    The generated archive section is skipped so pointers are never re-promoted.
    """
    facts: list[tuple[str, str]] = []
    heading = "General"
    for raw_line in content.splitlines():
        if raw_line.startswith("## "):
            heading = raw_line[3:].strip()
            continue
        if heading == _ARCHIVE_HEADING:
            continue
        if raw_line.startswith("- "):
            facts.append((heading, raw_line[2:].strip()))
    return facts


def _parse_notes(content: str) -> dict[str, list[str]]:
    """Collect non-bullet lines (prose, indented bullets) per section; "" is the preamble."""
    notes: dict[str, list[str]] = {}
    heading = ""
    for raw_line in content.splitlines():
        if raw_line.startswith("## "):
            heading = raw_line[3:].strip()
            continue
        if heading == _ARCHIVE_HEADING or raw_line.startswith("# "):
            continue
        if not raw_line.strip() or raw_line.startswith("- "):
            continue
        notes.setdefault(heading, []).append(raw_line.rstrip())
    return notes


def _workspace_id(workspace: Any) -> str:
    if workspace is None:
        return ""
    if isinstance(workspace, dict):
        return str(workspace.get("id", ""))
    return str(getattr(workspace, "id", ""))


Compactor = Callable[[list[tuple[str, str]], int], list[tuple[str, str]]]
_LLM_TARGET_RATIO = 0.8


def _llm_compact(
    facts: list[tuple[str, str]],
    compactor: Compactor,
    budget_tokens: int,
    triggered_at: str,
    notes: dict[str, list[str]],
) -> list[tuple[str, str]] | None:
    """Return LLM-compacted facts that fit the budget, or None to fall back."""
    try:
        compacted = compactor(facts, int(budget_tokens * _LLM_TARGET_RATIO))
    except Exception as exc:
        logger.warning("LLM compaction failed, using fallback: %s", exc)
        return None
    if not compacted:
        return None
    rendered = _render_memory(compacted, len(facts), triggered_at, notes)
    if count_tokens(rendered) > budget_tokens:
        logger.warning("LLM compaction exceeded budget, using fallback")
        return None
    return compacted


def _render_memory(
    facts: list[tuple[str, str]],
    promoted_count: int,
    triggered_at: str,
    notes: dict[str, list[str]] | None = None,
) -> str:
    notes = notes or {}
    by_heading: dict[str, list[str]] = {}
    for heading, text in facts:
        by_heading.setdefault(heading, []).append(text)

    lines = ["# Memory", ""]
    if notes.get(""):
        lines.extend(notes[""])
        lines.append("")
    headings = list(by_heading) + [h for h in notes if h and h not in by_heading]
    for heading in headings:
        lines.append(f"## {heading}")
        lines.extend(notes.get(heading, []))
        lines.extend(f"- {item}" for item in by_heading.get(heading, []))
        lines.append("")

    if promoted_count:
        lines.append(f"## {_ARCHIVE_HEADING}")
        lines.append(
            f"- {promoted_count} superseded fact(s) archived to the global vector "
            f"store on {triggered_at} (see the vector store for full provenance)."
        )
        lines.append("")

    return "\n".join(lines).rstrip() + "\n"


def compact_memory(
    root_path: str | Path,
    global_db_path: str | None = None,
    budgets: MemoryBudgets | None = None,
    workspace: Any = None,
    compactor: Compactor | None = None,
) -> CompactionOutcome:
    """Compact MEMORY.md when it exceeds its configured token budget.

    Splits the facts (duplicates included; deduplication only applies to the
    in-memory context) and, if a ``compactor`` (LLM rewrite) is given and its
    result fits the budget, archives all original facts to the durable vector
    store and keeps the rewritten ones. Otherwise promotes the oldest half to
    the vector store (with section/workspace provenance) and replaces them
    with a compact archive pointer. If vector promotion fails, no facts are
    dropped and the failure is recorded for observability.
    """
    if budgets is None:
        budgets = MemoryBudgets()

    content = read_memory(root_path)
    facts = _parse_facts(content)
    notes = _parse_notes(content)
    size_before = count_tokens(content)
    triggered_at = datetime.now(timezone.utc).isoformat()

    outcome = CompactionOutcome(
        tier="memory",
        triggered_at=triggered_at,
        facts_before=len(facts),
        facts_after=len(facts),
        facts_promoted=0,
        size_before_tokens=size_before,
        size_after_tokens=size_before,
        succeeded=True,
    )

    if size_before <= budgets.memory_tokens:
        outcome.skipped_reason = "no_pressure"
        record_state(root_path, budgets, check_pressure(root_path, budgets), outcome)
        return outcome

    # At least one fact moves so a single oversized fact still makes progress.
    split = max(1, len(facts) // 2) if facts else 0
    to_promote = facts[:split]
    to_keep = facts[split:]

    if compactor is not None:
        compacted = _llm_compact(facts, compactor, budgets.memory_tokens, triggered_at, notes)
        if compacted is not None:
            to_promote, to_keep = facts, compacted

    promoted_ids: list[str] = []
    try:
        from .sqlite import SQLiteMemory

        with SQLiteMemory(db_path=global_db_path) as sqlite_memory:
            try:
                for heading, text in to_promote:
                    metadata = {
                        "tier": 3,
                        "source": "memory_md_compaction",
                        "section": heading,
                        "workspace_id": _workspace_id(workspace),
                        "created_at": triggered_at,
                    }
                    promoted_ids.append(sqlite_memory.create(text, metadata=metadata))
            except Exception:
                # Roll back so a retry does not store the same facts twice.
                for record_id in promoted_ids:
                    sqlite_memory.delete(record_id)
                raise
    except Exception as exc:
        logger.warning("Vector promotion failed during compaction: %s", exc, exc_info=True)
        outcome.succeeded = False
        outcome.error = f"promotion_failed: {exc}"
        record_state(root_path, budgets, check_pressure(root_path, budgets), outcome)
        return outcome

    promoted_count = len(promoted_ids)
    new_content = _render_memory(to_keep, promoted_count, triggered_at, notes)
    write_memory(root_path, new_content)

    outcome.facts_after = len(to_keep)
    outcome.facts_promoted = promoted_count
    outcome.size_after_tokens = count_tokens(new_content)
    if outcome.size_after_tokens > budgets.memory_tokens:
        logger.warning(
            "MEMORY.md is still over budget after compaction (%d > %d tokens)",
            outcome.size_after_tokens,
            budgets.memory_tokens,
        )

    record_state(root_path, budgets, check_pressure(root_path, budgets), outcome)
    return outcome
