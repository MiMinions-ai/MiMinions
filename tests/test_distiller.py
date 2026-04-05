"""Unit tests for session memory distillation pipeline."""

from types import SimpleNamespace

import pytest

from miminions.memory import DistillationResult, MemoryDistiller
from miminions.session.store import JsonlSessionStore


class _FakeSQLiteMemory:
    created: list[tuple[str, dict]] = []

    def __init__(self, db_path: str):
        self.db_path = db_path

    def create(self, text: str, metadata: dict | None = None) -> str:
        self.__class__.created.append((text, metadata or {}))
        return f"fake-{len(self.__class__.created)}"

    def close(self) -> None:
        return None


def _append_transcript(root, session_id="s1"):
    store = JsonlSessionStore(root)
    store.append(session_id, "user", "Please enforce black formatting in this repo")
    store.append(session_id, "assistant", "Will do. I will keep formatting deterministic.")
    return session_id


def test_distillation_result_defaults():
    result = DistillationResult()

    assert result.history_summary == ""
    assert result.workspace_facts == []
    assert result.global_insights == []
    assert result.promoted_counts == {"tier1": 0, "tier2": 0, "tier3": 0}
    assert result.dropped_reasons == []


def test_memory_distiller_uses_explicit_global_path(tmp_path):
    db_path = str(tmp_path / "global.db")
    distiller = MemoryDistiller(lambda **_: {}, global_db_path=db_path)

    assert distiller.global_db_path == db_path


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

    assert result.promoted_counts == {"tier1": 0, "tier2": 0, "tier3": 0}
    assert any("empty_session" in reason for reason in result.dropped_reasons)


def test_distill_session_rejects_invalid_llm_schema(tmp_path):
    session_id = _append_transcript(tmp_path)
    distiller = MemoryDistiller(
        lambda **_: {
            "history_summary": "ok",
            "workspace_facts": "not-a-list",
            "global_insights": [],
        }
    )

    result = distiller.distill_session(workspace={}, root_path=str(tmp_path), session_id=session_id)

    assert result.promoted_counts == {"tier1": 0, "tier2": 0, "tier3": 0}
    assert any("invalid_schema" in reason for reason in result.dropped_reasons)


def test_distill_session_promotes_history_and_workspace_memory(tmp_path, monkeypatch):
    _FakeSQLiteMemory.created = []
    monkeypatch.setattr("miminions.memory.distiller.SQLiteMemory", _FakeSQLiteMemory)

    session_id = _append_transcript(tmp_path)

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

    assert result.promoted_counts["tier1"] == 1
    assert result.promoted_counts["tier2"] == 2
    assert result.promoted_counts["tier3"] == 0

    history_text = (tmp_path / "memory" / "HISTORY.md").read_text(encoding="utf-8")
    assert "- Completed formatting setup and captured style conventions." in history_text

    memory_text = (tmp_path / "memory" / "MEMORY.md").read_text(encoding="utf-8")
    assert "## Project Facts" in memory_text
    assert "- The project uses black for code formatting." in memory_text
    assert "- Tests run with pytest." in memory_text
    assert memory_text.count("- Tests run with pytest.") == 1


def test_distill_session_filters_global_insights_and_persists_only_high_signal(tmp_path, monkeypatch):
    _FakeSQLiteMemory.created = []
    monkeypatch.setattr("miminions.memory.distiller.SQLiteMemory", _FakeSQLiteMemory)

    session_id = _append_transcript(tmp_path)

    def llm_filter(**_kwargs):
        return {
            "history_summary": "Captured durable preferences and coding standards.",
            "workspace_facts": [],
            "global_insights": [
                {
                    "text": "The user prefers concise commit messages with imperative mood.",
                    "category": "user_preference",
                    "confidence": 0.95,
                },
                {
                    "text": "TODO fix this later",
                    "category": "coding_standard",
                    "confidence": 0.99,
                },
                {
                    "text": "Always run tests before pushing code to remote branches.",
                    "category": "coding_standard",
                    "confidence": 0.60,
                },
                {
                    "text": "The user prefers concise commit messages with imperative mood.",
                    "category": "user_preference",
                    "confidence": 0.98,
                },
                {
                    "text": "Maintain a reproducible release checklist for deployments.",
                    "category": "unknown",
                    "confidence": 0.95,
                },
            ],
        }

    workspace = SimpleNamespace(id="ws-2", name="MiMinions")
    distiller = MemoryDistiller(llm_filter, global_db_path=str(tmp_path / "global.db"))

    result = distiller.distill_session(
        workspace=workspace,
        root_path=str(tmp_path),
        session_id=session_id,
    )

    assert result.promoted_counts["tier3"] == 1
    assert len(_FakeSQLiteMemory.created) == 1

    text, metadata = _FakeSQLiteMemory.created[0]
    assert text == "The user prefers concise commit messages with imperative mood."
    assert metadata["tier"] == 3
    assert metadata["category"] == "user_preference"
    assert metadata["workspace_id"] == "ws-2"
    assert metadata["workspace_name"] == "MiMinions"
    assert metadata["session_id"] == session_id
    assert metadata["source"] == "distiller"
    assert "created_at" in metadata

    assert any("non-durable" in reason for reason in result.dropped_reasons)
    assert any("below threshold" in reason for reason in result.dropped_reasons)
    assert any("duplicate" in reason for reason in result.dropped_reasons)
    assert any("unsupported category" in reason for reason in result.dropped_reasons)
