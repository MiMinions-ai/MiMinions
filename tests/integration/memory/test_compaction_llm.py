"""Tests for semantic dedupe and LLM-driven MEMORY.md compaction."""

from __future__ import annotations

import sys
from types import SimpleNamespace
from typing import ClassVar, Self

import pytest

from miminions.memory.budget import MemoryBudgets
from miminions.memory.compaction import _dedupe_facts, compact_memory
from miminions.memory.md_store import read_memory, upsert_memory_section
from miminions.workspace_fs.bootstrap import init_workspace


class _FakeSQLiteMemory:
    created: ClassVar[list[tuple[str, dict]]] = []

    def __init__(self, db_path: str | None = None):
        self.db_path = db_path

    def create(self, text: str, metadata: dict | None = None) -> str:
        self.__class__.created.append((text, metadata or {}))
        return f"fake-{len(self.__class__.created)}"

    def __enter__(self) -> Self:
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        return None


class _FailingSQLiteMemory:
    def __init__(self, db_path: str | None = None):
        raise RuntimeError("vector store down")


def _patch_sqlite_memory(monkeypatch, sqlite_memory_cls):
    monkeypatch.setitem(
        sys.modules,
        "miminions.memory.sqlite",
        SimpleNamespace(SQLiteMemory=sqlite_memory_cls),
    )


def _patch_embeddings(monkeypatch, vectors: dict[str, list[float]]):
    class _FakeTextEmbedding:
        def __init__(self, model_name: str):
            self.model_name = model_name

        def embed(self, texts):
            return [vectors[text] for text in texts]

    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=_FakeTextEmbedding))


@pytest.fixture(autouse=True)
def _no_real_embedding_model(monkeypatch):
    """Keep tests offline: the default embedding model fails to load."""

    class _Unavailable:
        def __init__(self, model_name: str):
            raise RuntimeError("model unavailable")

    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=_Unavailable))


def _seed_facts(root_path, count: int) -> None:
    facts = [f"fact number {i} about the workspace with enough text to add size" for i in range(count)]
    upsert_memory_section(root_path, "Project Facts", facts)


# --- semantic dedupe -------------------------------------------------------


def test_dedupe_drops_semantically_similar_fact_and_keeps_first(monkeypatch):
    _patch_embeddings(
        monkeypatch,
        {"uses pytest": [1.0, 0.0], "tests run with pytest": [0.99, 0.05], "uses black": [0.0, 1.0]},
    )
    facts = [("A", "uses pytest"), ("A", "tests run with pytest"), ("B", "uses black")]

    deduped, dropped = _dedupe_facts(facts, threshold=0.92)

    assert deduped == [("A", "uses pytest"), ("B", "uses black")], f"expect near-duplicate dropped keeping first as [('A','uses pytest'),('B','uses black')], got {deduped}"
    assert dropped == 1, f"expect 1 fact dropped as 1, got {dropped}"


def test_dedupe_keeps_dissimilar_facts(monkeypatch):
    _patch_embeddings(monkeypatch, {"alpha": [1.0, 0.0], "beta": [0.0, 1.0]})

    deduped, dropped = _dedupe_facts([("A", "alpha"), ("A", "beta")])

    assert len(deduped) == 2, f"expect both dissimilar facts kept as 2, got {len(deduped)}"
    assert dropped == 0, f"expect nothing dropped as 0, got {dropped}"


def test_dedupe_exact_duplicates_are_dropped_without_embeddings():
    facts = [("A", "Same Fact"), ("B", "same fact"), ("A", "other")]

    deduped, dropped = _dedupe_facts(facts)

    assert deduped == [("A", "Same Fact"), ("A", "other")], f"expect case-insensitive exact duplicate dropped, got {deduped}"
    assert dropped == 1, f"expect 1 dropped as 1, got {dropped}"


def test_dedupe_falls_back_to_exact_when_embedding_model_unavailable():
    facts = [("A", "uses pytest"), ("A", "tests run with pytest")]

    deduped, dropped = _dedupe_facts(facts)

    assert deduped == facts, f"expect facts kept when model unavailable as {facts}, got {deduped}"
    assert dropped == 0, f"expect nothing dropped as 0, got {dropped}"


def test_dedupe_handles_empty_and_single_fact_lists():
    assert _dedupe_facts([]) == ([], 0), "expect empty list returns ([], 0)"
    assert _dedupe_facts([("A", "only")]) == ([("A", "only")], 0), "expect single fact returned as is"


def test_dedupe_handles_zero_vector_without_error(monkeypatch):
    _patch_embeddings(monkeypatch, {"a": [0.0, 0.0], "b": [1.0, 0.0]})

    deduped, dropped = _dedupe_facts([("A", "a"), ("A", "b")])

    assert len(deduped) == 2, f"expect zero vector does not crash or match as 2 kept, got {len(deduped)}"
    assert dropped == 0, f"expect 0 dropped as 0, got {dropped}"


def test_dedupe_rejects_invalid_threshold():
    with pytest.raises(AssertionError):
        _dedupe_facts([("A", "a"), ("A", "b")], threshold=0.0)


# --- LLM compactor ---------------------------------------------------------


def test_llm_compactor_replaces_facts_and_archives_originals(tmp_path, monkeypatch):
    _FakeSQLiteMemory.created = []
    _patch_sqlite_memory(monkeypatch, _FakeSQLiteMemory)
    init_workspace(tmp_path)
    _seed_facts(tmp_path, 30)
    targets: list[int] = []

    def compactor(facts, target_tokens):
        targets.append(target_tokens)
        return [("Project Facts", "workspace has many numbered facts")]

    outcome = compact_memory(
        tmp_path, global_db_path=":memory:", budgets=MemoryBudgets(memory_tokens=150), compactor=compactor
    )

    content = read_memory(tmp_path)
    assert outcome.succeeded is True, f"expect compaction succeeded as True, got {outcome.succeeded}"
    assert targets == [120], f"expect compactor target 80% of 150 tokens as [120], got {targets}"
    assert outcome.facts_promoted == 30, f"expect all 30 original facts archived as 30, got {outcome.facts_promoted}"
    assert len(_FakeSQLiteMemory.created) == 30, f"expect 30 records in vector store as 30, got {len(_FakeSQLiteMemory.created)}"
    assert "workspace has many numbered facts" in content, f"expect rewritten fact in MEMORY.md as True, got {content}"
    assert "fact number 0" not in content, f"expect original facts removed as True, got {'fact number 0' in content}"
    assert outcome.facts_after == 1, f"expect 1 fact remaining as 1, got {outcome.facts_after}"


@pytest.mark.parametrize(
    "compactor",
    [
        pytest.param(lambda facts, target: (_ for _ in ()).throw(RuntimeError("llm down")), id="raises"),
        pytest.param(lambda facts, target: [], id="empty"),
        pytest.param(lambda facts, target: facts, id="over-budget"),
    ],
)
def test_llm_compactor_failures_fall_back_to_promote_oldest_half(tmp_path, monkeypatch, compactor):
    _FakeSQLiteMemory.created = []
    _patch_sqlite_memory(monkeypatch, _FakeSQLiteMemory)
    init_workspace(tmp_path)
    _seed_facts(tmp_path, 10)

    outcome = compact_memory(
        tmp_path, global_db_path=":memory:", budgets=MemoryBudgets(memory_tokens=50), compactor=compactor
    )

    content = read_memory(tmp_path)
    assert outcome.succeeded is True, f"expect fallback compaction succeeded as True, got {outcome.succeeded}"
    assert outcome.facts_promoted == 5, f"expect fallback promotes half of 10 as 5, got {outcome.facts_promoted}"
    assert "fact number 9" in content, f"expect newest fact retained as True, got {'fact number 9' in content}"
    assert "fact number 0" not in content, f"expect oldest fact archived as True, got {'fact number 0' in content}"


def test_llm_compactor_not_called_when_under_budget(tmp_path):
    init_workspace(tmp_path)
    _seed_facts(tmp_path, 3)
    calls: list[int] = []

    outcome = compact_memory(
        tmp_path,
        budgets=MemoryBudgets(memory_tokens=100_000),
        compactor=lambda facts, target: calls.append(target) or facts,
    )

    assert calls == [], f"expect compactor not called under budget as [], got {calls}"
    assert outcome.facts_promoted == 0, f"expect nothing promoted as 0, got {outcome.facts_promoted}"


def test_llm_compactor_keeps_memory_when_archiving_fails(tmp_path, monkeypatch):
    _patch_sqlite_memory(monkeypatch, _FailingSQLiteMemory)
    init_workspace(tmp_path)
    _seed_facts(tmp_path, 30)
    before = read_memory(tmp_path)

    outcome = compact_memory(
        tmp_path,
        global_db_path=":memory:",
        budgets=MemoryBudgets(memory_tokens=150),
        compactor=lambda facts, target: [("Project Facts", "short")],
    )

    assert outcome.succeeded is False, f"expect failed archiving reported as False, got {outcome.succeeded}"
    assert read_memory(tmp_path) == before, "expect MEMORY.md untouched when archiving fails"
