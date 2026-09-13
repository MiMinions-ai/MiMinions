"""Tests for pressure-triggered MEMORY.md compaction and promotion."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import ClassVar, Self

from miminions.memory.budget import MemoryBudgets, load_state
from miminions.memory.compaction import compact_memory
from miminions.memory.md_store import read_memory, upsert_memory_section
from miminions.workspace_fs.bootstrap import init_workspace


class _FakeSQLiteMemory:
    created: ClassVar[list[tuple[str, dict]]] = []

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def create(self, text: str, metadata: dict | None = None) -> str:
        self.__class__.created.append((text, metadata or {}))
        return f"fake-{len(self.__class__.created)}"

    def close(self) -> None:
        return None

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()


class _FailingSQLiteMemory:
    def __init__(self, db_path: str | None = None):
        raise RuntimeError("fastembed unavailable")


def _patch_sqlite_memory(monkeypatch, sqlite_memory_cls):
    monkeypatch.setitem(
        sys.modules,
        "miminions.memory.sqlite",
        SimpleNamespace(SQLiteMemory=sqlite_memory_cls),
    )


def _seed_facts(root_path, count: int) -> None:
    facts = [f"fact number {i} about the workspace with enough text to add size" for i in range(count)]
    upsert_memory_section(root_path, "Project Facts", facts)


def test_compact_memory_is_noop_when_under_budget(tmp_path):
    init_workspace(tmp_path)
    _seed_facts(tmp_path, 3)
    budgets = MemoryBudgets(memory_tokens=100_000)

    outcome = compact_memory(tmp_path, budgets=budgets)

    assert outcome.succeeded is True, f"expect under-budget compaction to report succeeded as True, got {outcome.succeeded}"
    assert outcome.facts_promoted == 0, f"expect no facts promoted when under budget as 0, got {outcome.facts_promoted}"
    assert outcome.facts_before == outcome.facts_after, f"expect fact count unchanged when under budget as {outcome.facts_before}, got {outcome.facts_after}"


def test_compact_memory_promotes_oldest_half_when_over_budget(tmp_path, monkeypatch):
    _FakeSQLiteMemory.created = []
    _patch_sqlite_memory(monkeypatch, _FakeSQLiteMemory)
    init_workspace(tmp_path)
    _seed_facts(tmp_path, 10)
    budgets = MemoryBudgets(memory_tokens=50)

    outcome = compact_memory(tmp_path, global_db_path=":memory:", budgets=budgets, workspace={"id": "ws-1"})

    assert outcome.succeeded is True, f"expect over-budget compaction to report succeeded as True, got {outcome.succeeded}"
    assert outcome.facts_promoted == 5, f"expect half of 10 facts promoted to vector store as 5, got {outcome.facts_promoted}"
    assert len(_FakeSQLiteMemory.created) == 5, f"expect 5 records written to fake vector store as 5, got {len(_FakeSQLiteMemory.created)}"
    promoted_metadata = _FakeSQLiteMemory.created[0][1]
    assert promoted_metadata["workspace_id"] == "ws-1", f"expect promoted record carries workspace_id provenance as 'ws-1', got {promoted_metadata['workspace_id']}"
    assert promoted_metadata["source"] == "memory_md_compaction", f"expect promoted record source as 'memory_md_compaction', got {promoted_metadata['source']}"

    remaining_content = read_memory(tmp_path)
    assert "Archived Facts" in remaining_content, f"expect archive pointer section present in MEMORY.md as True, got 'Archived Facts' in remaining_content: {'Archived Facts' in remaining_content}"
    assert "fact number 9" in remaining_content, f"expect newest fact retained in MEMORY.md as True, got 'fact number 9' in remaining_content: {'fact number 9' in remaining_content}"
    assert "fact number 0" not in remaining_content, f"expect oldest fact removed from MEMORY.md as True, got 'fact number 0' in remaining_content: {'fact number 0' in remaining_content}"


def test_compact_memory_deduplicates_facts_before_promotion(tmp_path, monkeypatch):
    _FakeSQLiteMemory.created = []
    _patch_sqlite_memory(monkeypatch, _FakeSQLiteMemory)
    init_workspace(tmp_path)
    upsert_memory_section(tmp_path, "Project Facts", ["duplicate fact", "duplicate fact", "unique fact"])
    budgets = MemoryBudgets(memory_tokens=1)

    outcome = compact_memory(tmp_path, global_db_path=":memory:", budgets=budgets)

    assert outcome.facts_dropped_duplicate == 1, f"expect one duplicate fact dropped as 1, got {outcome.facts_dropped_duplicate}"


def test_compact_memory_preserves_facts_when_promotion_fails(tmp_path, monkeypatch):
    _patch_sqlite_memory(monkeypatch, _FailingSQLiteMemory)
    init_workspace(tmp_path)
    _seed_facts(tmp_path, 10)
    budgets = MemoryBudgets(memory_tokens=50)
    content_before = read_memory(tmp_path)

    outcome = compact_memory(tmp_path, global_db_path=":memory:", budgets=budgets)

    assert outcome.succeeded is False, f"expect failed promotion to report succeeded as False, got {outcome.succeeded}"
    assert "promotion_failed" in outcome.error, f"expect error mentions promotion_failed as True, got {outcome.error}"
    content_after = read_memory(tmp_path)
    assert content_after == content_before, f"expect MEMORY.md unchanged when promotion fails, got a diff between before/after content"


def test_compact_memory_is_idempotent_across_repeated_calls(tmp_path, monkeypatch):
    _FakeSQLiteMemory.created = []
    _patch_sqlite_memory(monkeypatch, _FakeSQLiteMemory)
    init_workspace(tmp_path)
    _seed_facts(tmp_path, 20)
    budgets = MemoryBudgets(memory_tokens=50)

    first = compact_memory(tmp_path, global_db_path=":memory:", budgets=budgets)
    second = compact_memory(tmp_path, global_db_path=":memory:", budgets=budgets)

    assert first.facts_promoted == 10, f"expect first compaction promotes half of 20 facts as 10, got {first.facts_promoted}"
    assert second.facts_after <= first.facts_after, f"expect repeated compaction to not grow fact count, got first={first.facts_after} second={second.facts_after}"

    state = load_state(tmp_path)
    assert len(state["compaction_history"]) == 2, f"expect two recorded compaction outcomes as 2, got {len(state['compaction_history'])}"
