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
_EMBED_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
_SEMANTIC_THRESHOLD = 0.92


def _parse_facts(content: str) -> list[tuple[str, str]]:
    """Return (section_heading, fact_text) for every bullet line in MEMORY.md."""
    facts: list[tuple[str, str]] = []
    heading = "General"
    for raw_line in content.splitlines():
        line = raw_line.strip()
        if line.startswith("## "):
            heading = line[3:].strip()
            continue
        if line.startswith("- "):
            facts.append((heading, line[2:].strip()))
    return facts


def _exact_dedupe(facts: list[tuple[str, str]]) -> list[tuple[str, str]]:
    seen: set[str] = set()
    deduped: list[tuple[str, str]] = []
    for heading, text in facts:
        key = text.casefold()
        if key not in seen:
            seen.add(key)
            deduped.append((heading, text))
    return deduped


def _semantic_dedupe(
    facts: list[tuple[str, str]], threshold: float
) -> list[tuple[str, str]]:
    """Drop facts whose embedding cosine similarity to a kept fact >= threshold."""
    assert 0.0 < threshold <= 1.0
    if len(facts) < 2:
        return facts
    try:
        import numpy as np
        from fastembed import TextEmbedding

        model = TextEmbedding(_EMBED_MODEL)
        vectors = np.array(list(model.embed([text for _, text in facts])), dtype=float)
    except Exception as exc:  # fastembed missing or model unavailable
        logger.warning("Semantic dedupe unavailable, using exact match only: %s", exc)
        return facts

    norms = np.linalg.norm(vectors, axis=1, keepdims=True)
    vectors = vectors / np.maximum(norms, 1e-12)
    kept: list[int] = []
    for i in range(len(facts)):
        if kept and float(np.max(vectors[kept] @ vectors[i])) >= threshold:
            continue
        kept.append(i)
    return [facts[i] for i in kept]


def _dedupe_facts(
    facts: list[tuple[str, str]], threshold: float = _SEMANTIC_THRESHOLD
) -> tuple[list[tuple[str, str]], int]:
    """Drop exact (case-insensitive) then semantically near-duplicate facts.

    The first occurrence is kept. Falls back to exact matching if fastembed
    is not installed.
    """
    deduped = _semantic_dedupe(_exact_dedupe(facts), threshold)
    return deduped, len(facts) - len(deduped)


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
) -> list[tuple[str, str]] | None:
    """Return LLM-compacted facts that fit the budget, or None to fall back."""
    try:
        compacted = compactor(facts, int(budget_tokens * _LLM_TARGET_RATIO))
    except Exception as exc:
        logger.warning("LLM compaction failed, using fallback: %s", exc)
        return None
    if not compacted:
        return None
    rendered = _render_memory(compacted, len(facts), triggered_at)
    if count_tokens(rendered) > budget_tokens:
        logger.warning("LLM compaction exceeded budget, using fallback")
        return None
    return compacted


def _render_memory(facts: list[tuple[str, str]], promoted_count: int, triggered_at: str) -> str:
    by_heading: dict[str, list[str]] = {}
    for heading, text in facts:
        by_heading.setdefault(heading, []).append(text)

    lines = ["# Memory", ""]
    for heading, items in by_heading.items():
        lines.append(f"## {heading}")
        lines.extend(f"- {item}" for item in items)
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

    Deduplicates facts, then, if a ``compactor`` (LLM rewrite) is given and its
    result fits the budget, archives all original facts to the durable vector
    store and keeps the rewritten ones. Otherwise promotes the oldest half to
    the vector store (with section/workspace provenance) and replaces them
    with a compact archive pointer. If vector promotion fails, no facts are
    dropped and the failure is recorded for observability.
    """
    if budgets is None:
        budgets = MemoryBudgets()

    content = read_memory(root_path)
    raw_facts = _parse_facts(content)
    facts, dropped_duplicates = _dedupe_facts(raw_facts)
    size_before = count_tokens(content)
    triggered_at = datetime.now(timezone.utc).isoformat()

    outcome = CompactionOutcome(
        tier="memory",
        triggered_at=triggered_at,
        facts_before=len(raw_facts),
        facts_after=len(raw_facts),
        facts_promoted=0,
        facts_dropped_duplicate=dropped_duplicates,
        size_before_tokens=size_before,
        size_after_tokens=size_before,
        succeeded=True,
    )

    if size_before <= budgets.memory_tokens:
        outcome.error = "no_pressure: under budget, no compaction needed"
        record_state(root_path, budgets, check_pressure(root_path, budgets), outcome)
        return outcome

    split = len(facts) // 2
    to_promote = facts[:split]
    to_keep = facts[split:]

    if compactor is not None:
        compacted = _llm_compact(facts, compactor, budgets.memory_tokens, triggered_at)
        if compacted is not None:
            to_promote, to_keep = facts, compacted

    promoted_count = 0
    try:
        from .sqlite import SQLiteMemory

        with SQLiteMemory(db_path=global_db_path) as sqlite_memory:
            for heading, text in to_promote:
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

    new_content = _render_memory(to_keep, promoted_count, triggered_at)
    write_memory(root_path, new_content)

    outcome.facts_after = len(to_keep)
    outcome.facts_promoted = promoted_count
    outcome.size_after_tokens = count_tokens(new_content)

    record_state(root_path, budgets, check_pressure(root_path, budgets), outcome)
    return outcome
