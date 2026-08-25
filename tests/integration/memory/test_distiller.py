"""Unit tests for session memory distillation pipeline."""

import logging
import sys
from types import SimpleNamespace
from typing import ClassVar, Self

import pytest

from miminions.memory import DistillationResult, MemoryDistiller
from miminions.utils.session import append_transcript


class _FakeSQLiteMemory:
    created: ClassVar[list[tuple[str, dict]]] = []

    def __init__(self, db_path: str):
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


def _patch_sqlite_memory(monkeypatch, sqlite_memory_cls):
    monkeypatch.setitem(
        sys.modules,
        "miminions.memory.sqlite",
        SimpleNamespace(SQLiteMemory=sqlite_memory_cls),
    )


def test_distillation_result_defaults():
    result = DistillationResult()

    assert result.history_summary == "", f"expect DistillationResult default history_summary is empty string '', got {result.history_summary}"
    assert result.workspace_facts == [], f"expect [] as [], got {result.workspace_facts}"
    assert result.global_insights == [], f"expect [] as [], got {result.global_insights}"
    assert result.promoted_counts == {"tier1": 0, "tier2": 0, "tier3": 0}, f"expect {{'tier1': 0, 'tier2': 0, 'tier3': 0}}, got {result.promoted_counts}"
    assert result.dropped_reasons == [], f"expect [] as [], got {result.dropped_reasons}"


def test_memory_distiller_uses_explicit_global_path(tmp_path):
    db_path = str(tmp_path / "global.db")
    distiller = MemoryDistiller(lambda **_: {}, global_db_path=db_path)

    assert distiller.global_db_path == db_path, f"expect db_path as {db_path}, got {distiller.global_db_path}"


def test_memory_distiller_rejects_non_callable_filter():
    with pytest.raises(TypeError, match="llm_filter must be callable"):
        MemoryDistiller(None)


def test_distill_session_handles_empty_session_gracefully(tmp_path):
    distiller = MemoryDistiller(
        lambda **_: {
            "history_summary": "summary",
            "workspace_facts": ["fact"],
            "global_insights": [],
        }
    )

    result = distiller.distill_session(workspace={}, root_path=str(tmp_path), session_id="missing")

    assert result.promoted_counts == {"tier1": 0, "tier2": 0, "tier3": 0}, f"expect {{'tier1': 0, 'tier2': 0, 'tier3': 0}}, got {result.promoted_counts}"
    has_empty_session_reason = any("empty_session" in reason for reason in result.dropped_reasons)
    assert has_empty_session_reason, f"expect at least one item matching 'empty_session' in reason as {True}, got {has_empty_session_reason} with dropped_reasons {result.dropped_reasons}"


def test_distill_session_accepts_partial_llm_output_with_permissive_defaults(tmp_path):
    session_id = append_transcript(tmp_path)
    distiller = MemoryDistiller(
        lambda **_: {
            "history_summary": "ok",
            "workspace_facts": "not-a-list",
            # global_insights intentionally omitted
        }
    )

    result = distiller.distill_session(workspace={}, root_path=str(tmp_path), session_id=session_id)

    assert result.promoted_counts["tier1"] == 1, f"expect partial LLM output promotes one history summary to tier1 as 1, got {result.promoted_counts['tier1']}"
    assert result.promoted_counts["tier2"] == 1, f"expect non-list workspace_facts is coerced into one tier2 fact as 1, got {result.promoted_counts['tier2']}"
    assert result.promoted_counts["tier3"] == 0, f"expect tier3 promoted count to be 0 when global_insights missing, got {result.promoted_counts['tier3']}"
    assert result.dropped_reasons == [], f"expect [] as [], got {result.dropped_reasons}"


def test_distill_session_promotes_history_and_workspace_memory(tmp_path, monkeypatch):
    _FakeSQLiteMemory.created = []
    _patch_sqlite_memory(monkeypatch, _FakeSQLiteMemory)

    session_id = append_transcript(tmp_path)

    def llm_filter(**_kwargs):
        return {
            "history_summary": "Completed formatting setup and captured style conventions.",
            "workspace_facts": [
                "The project uses black for code formatting.",
                "Tests run with pytest.",
                "Tests run with pytest.",
            ],
            "global_insights": [],
        }

    workspace = SimpleNamespace(id="ws-1", name="MiMinions")
    distiller = MemoryDistiller(llm_filter, global_db_path=str(tmp_path / "global.db"))

    result = distiller.distill_session(
        workspace=workspace,
        root_path=str(tmp_path),
        session_id=session_id,
    )

    assert result.promoted_counts["tier1"] == 1, f"expect distillation promotes one history summary to tier1 as 1, got {result.promoted_counts['tier1']}"
    assert result.promoted_counts["tier2"] == 2, f"expect distillation promotes two unique workspace facts to tier2 as 2, got {result.promoted_counts['tier2']}"
    assert result.promoted_counts["tier3"] == 0, f"expect tier3 promoted count to remain 0 when no global insights are returned, got {result.promoted_counts['tier3']}"

    history_text = (tmp_path / "memory" / "HISTORY.md").read_text(encoding="utf-8")
    assert "- Completed formatting setup and captured style conventions." in history_text, f"expect contains '- Completed formatting setup and captured style conventions.', got {history_text}"

    memory_text = (tmp_path / "memory" / "MEMORY.md").read_text(encoding="utf-8")
    assert "## Project Facts" in memory_text, f"expect contains '## Project Facts', got {memory_text}"
    assert "- The project uses black for code formatting." in memory_text, f"expect contains '- The project uses black for code formatting.', got {memory_text}"
    assert "- Tests run with pytest." in memory_text, f"expect contains '- Tests run with pytest.', got {memory_text}"
    pytest_fact_count = memory_text.count("- Tests run with pytest.")
    assert pytest_fact_count == 1, f"expect duplicate workspace fact is written once in MEMORY.md as 1, got {pytest_fact_count}"


def test_distill_session_stores_global_insights_as_plain_text(tmp_path, monkeypatch):
    _FakeSQLiteMemory.created = []
    _patch_sqlite_memory(monkeypatch, _FakeSQLiteMemory)

    session_id = append_transcript(tmp_path)

    def llm_filter(**_kwargs):
        return {
            "history_summary": "Captured preferences and conventions.",
            "workspace_facts": [],
            "global_insights": [
                "The user prefers concise commit messages with imperative mood.",
                "Always run tests before pushing code to remote branches.",
                "The user prefers concise commit messages with imperative mood.",
                {"text": "Use deterministic formatting in CI to reduce noisy diffs."},
            ],
        }

    workspace = SimpleNamespace(id="ws-2", name="MiMinions")
    distiller = MemoryDistiller(llm_filter, global_db_path=str(tmp_path / "global.db"))

    result = distiller.distill_session(
        workspace=workspace,
        root_path=str(tmp_path),
        session_id=session_id,
    )

    assert result.promoted_counts["tier3"] == 3, f"expect distillation promotes three unique global insights to tier3 as 3, got {result.promoted_counts['tier3']}"
    created_count = len(_FakeSQLiteMemory.created)
    assert created_count == 3, f"expect SQLite memory create is called for each of three unique global insights as 3, got {created_count}"

    stored_texts = [entry[0] for entry in _FakeSQLiteMemory.created]
    assert "The user prefers concise commit messages with imperative mood." in stored_texts, f"expect contains 'The user prefers concise commit messages with imperative mood.', got {stored_texts}"
    assert "Always run tests before pushing code to remote branches." in stored_texts, f"expect contains 'Always run tests before pushing code to remote branches.', got {stored_texts}"
    assert "Use deterministic formatting in CI to reduce noisy diffs." in stored_texts, f"expect contains 'Use deterministic formatting in CI to reduce noisy diffs.', got {stored_texts}"

    _, metadata = _FakeSQLiteMemory.created[0]
    assert metadata["tier"] == 3, f"expect global insight metadata tier is 3, got {metadata['tier']}"
    assert metadata["workspace_id"] == "ws-2", f"expect global insight metadata workspace_id is 'ws-2', got {metadata['workspace_id']}"
    assert metadata["workspace_name"] == "MiMinions", f"expect global insight metadata workspace_name is 'MiMinions', got {metadata['workspace_name']}"
    assert metadata["session_id"] == session_id, f"expect session_id as {session_id}, got {metadata['session_id']}"
    assert metadata["source"] == "distiller", f"expect global insight metadata source is 'distiller', got {metadata['source']}"
    assert "created_at" in metadata, f"expect contains 'created_at', got {metadata}"

    assert result.dropped_reasons == [], f"expect [] as [], got {result.dropped_reasons}"


def test_distill_session_continues_when_sqlite_is_unavailable(tmp_path, monkeypatch, caplog):
    class _BrokenSQLiteMemory:
        def __init__(self, _db_path: str):
            raise RuntimeError("sqlite unavailable")

    _patch_sqlite_memory(monkeypatch, _BrokenSQLiteMemory)
    session_id = append_transcript(tmp_path)

    distiller = MemoryDistiller(
        lambda **_: {
            "history_summary": "Completed a short implementation session.",
            "workspace_facts": ["The repo uses pytest for tests."],
            "global_insights": ["Prefer running focused tests before full suite."],
        },
        global_db_path=str(tmp_path / "global.db"),
    )

    with caplog.at_level(logging.WARNING):
        result = distiller.distill_session(
            workspace=SimpleNamespace(id="ws-3", name="MiMinions"),
            root_path=str(tmp_path),
            session_id=session_id,
        )

    assert result.promoted_counts["tier1"] == 1, f"expect sqlite-unavailable path still promotes one history summary to tier1 as 1, got {result.promoted_counts['tier1']}"
    assert result.promoted_counts["tier2"] == 1, f"expect sqlite-unavailable path still promotes one workspace fact to tier2 as 1, got {result.promoted_counts['tier2']}"
    assert result.promoted_counts["tier3"] == 0, f"expect tier3 promoted count to stay 0 when sqlite is unavailable, got {result.promoted_counts['tier3']}"
    has_tier3_unavailable_reason = any("tier3_unavailable" in reason for reason in result.dropped_reasons)
    assert has_tier3_unavailable_reason, f"expect at least one item matching 'tier3_unavailable' in reason as {True}, got {has_tier3_unavailable_reason} with dropped_reasons {result.dropped_reasons}"
    # The failure must be observable, not just recorded in dropped_reasons.
    has_tier3_warning_log = any("Tier-3" in r.message for r in caplog.records)
    assert has_tier3_warning_log, f"expect at least one item matching 'Tier-3' in r.message as {True}, got {has_tier3_warning_log} with messages {[r.message for r in caplog.records]}"


def test_distill_session_warns_when_llm_filter_raises(tmp_path, caplog):
    def _exploding_filter(**_kwargs):
        raise RuntimeError("model exploded")

    session_id = append_transcript(tmp_path)
    distiller = MemoryDistiller(_exploding_filter, global_db_path=str(tmp_path / "global.db"))

    with caplog.at_level(logging.WARNING):
        result = distiller.distill_session(
            workspace=SimpleNamespace(id="ws-4", name="MiMinions"),
            root_path=str(tmp_path),
            session_id=session_id,
        )

    has_llm_filter_error_reason = any("llm_filter_error" in reason for reason in result.dropped_reasons)
    assert has_llm_filter_error_reason, f"expect at least one item matching 'llm_filter_error' in reason as {True}, got {has_llm_filter_error_reason} with dropped_reasons {result.dropped_reasons}"
    has_llm_filter_failed_log = any("LLM filter failed" in r.message for r in caplog.records)
    assert has_llm_filter_failed_log, f"expect at least one item matching 'LLM filter failed' in r.message as {True}, got {has_llm_filter_failed_log} with messages {[r.message for r in caplog.records]}"
