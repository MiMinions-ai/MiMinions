"""Pressure-triggered compaction of the MEMORY.md stable-fact tier."""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .budget import CompactionOutcome, MemoryBudgets, check_pressure, count_tokens, record_state
from .md_store import read_memory, write_memory

logger = logging.getLogger(__name__)

_ARCHIVE_HEADING = "Archived Facts"


def _parse_facts(content: str) -> list[tuple[int, str, str]]:
    """Return (line_number, section_heading, fact_text) for compactable bullets."""
    facts: list[tuple[int, str, str]] = []
    heading = "General"
    for line_number, raw_line in enumerate(content.splitlines()):
        line = raw_line.strip()
        if line.startswith("## "):
            heading = line[3:].strip()
            continue
        if line.startswith("- ") and heading.casefold() != _ARCHIVE_HEADING.casefold():
            facts.append((line_number, heading, line[2:].strip()))
    return facts


def _dedupe_facts(
    facts: list[tuple[int, str, str]],
) -> tuple[list[tuple[int, str, str]], set[int]]:
    """Return unique facts and line numbers of duplicate facts."""
    seen: set[str] = set()
    deduped: list[tuple[int, str, str]] = []
    duplicates: set[int] = set()
    for line_number, heading, text in facts:
        key = text.casefold()
        if key in seen:
            duplicates.add(line_number)
            continue
        seen.add(key)
        deduped.append((line_number, heading, text))
    return deduped, duplicates


def _workspace_id(workspace: Any) -> str:
    if workspace is None:
        return ""
    if isinstance(workspace, dict):
        return str(workspace.get("id", ""))
    return str(getattr(workspace, "id", ""))


def _render_memory(content: str, removed_lines: set[int], promoted_count: int, triggered_at: str) -> str:
    """Remove selected bullet lines while preserving all other source content."""
    lines = [
        line
        for line_number, line in enumerate(content.splitlines(keepends=True))
        if line_number not in removed_lines
    ]
    result = "".join(lines)
    if promoted_count:
        if result and not result.endswith("\n"):
            result += "\n"
        if result and not result.endswith("\n\n"):
            result += "\n"
        result += (
            f"## {_ARCHIVE_HEADING}\n"
            f"- {promoted_count} superseded fact(s) archived to the global vector "
            f"store on {triggered_at} (see the vector store for full provenance).\n"
        )
    return result


def compact_memory(
    root_path: str | Path,
    global_db_path: str | None = None,
    budgets: MemoryBudgets | None = None,
    workspace: Any = None,
) -> CompactionOutcome:
    """Compact MEMORY.md when it exceeds its configured token budget.

    Deduplicates facts, promoting the oldest facts to the durable vector store
    until the token budget is met or no facts remain. If vector promotion fails,
    no facts are dropped and the failure is recorded for observability.
    """
    if budgets is None:
        budgets = MemoryBudgets()

    content = read_memory(root_path)
    raw_facts = _parse_facts(content)
    facts, duplicate_lines = _dedupe_facts(raw_facts)
    size_before = count_tokens(content)
    triggered_at = datetime.now(timezone.utc).isoformat()

    outcome = CompactionOutcome(
        tier="memory",
        triggered_at=triggered_at,
        facts_before=len(raw_facts),
        facts_after=len(raw_facts),
        facts_promoted=0,
        facts_dropped_duplicate=len(duplicate_lines),
        size_before_tokens=size_before,
        size_after_tokens=size_before,
        succeeded=True,
    )

    if size_before <= budgets.memory_tokens:
        outcome.error = "no_pressure: under budget, no compaction needed"
        record_state(root_path, budgets, check_pressure(root_path, budgets), outcome)
        return outcome

    removed_lines = set(duplicate_lines)
    to_promote: list[tuple[int, str, str]] = []
    new_content = _render_memory(content, removed_lines, 0, triggered_at)
    if count_tokens(new_content) > budgets.memory_tokens:
        for fact in facts:
            candidate_lines = removed_lines | {fact[0]}
            candidate = _render_memory(content, candidate_lines, len(to_promote) + 1, triggered_at)
            to_promote.append(fact)
            removed_lines = candidate_lines
            new_content = candidate
            if count_tokens(candidate) <= budgets.memory_tokens:
                break

    promoted_count = 0
    if to_promote:
        try:
            from .sqlite import SQLiteMemory

            with SQLiteMemory(db_path=global_db_path) as sqlite_memory:
                for _, heading, text in to_promote:
                    metadata = {
                        "tier": 3,
                        "source": "memory_md_compaction",
                        "section": heading,
                        "workspace_id": _workspace_id(workspace),
                        "created_at": triggered_at,
                    }
                    sqlite_memory.create(text, metadata=metadata)
                    promoted_count += 1
        except Exception as exc:
            logger.warning("Vector promotion failed during compaction: %s", exc, exc_info=True)
            outcome.succeeded = False
            outcome.error = f"promotion_failed: {exc}"
            record_state(root_path, budgets, check_pressure(root_path, budgets), outcome)
            return outcome

    if removed_lines:
        write_memory(root_path, new_content)

    outcome.facts_after = len(facts) - promoted_count
    outcome.facts_promoted = promoted_count
    outcome.size_after_tokens = count_tokens(new_content)
    if outcome.size_after_tokens > budgets.memory_tokens:
        outcome.succeeded = False
        outcome.error = "budget_unmet: non-compacting content exceeds the memory budget"

    record_state(root_path, budgets, check_pressure(root_path, budgets), outcome)
    return outcome
