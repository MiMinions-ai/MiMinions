"""Unit tests for memory distiller scaffolding."""

import pytest

from miminions.memory import DistillationResult, MemoryDistiller


def _fake_llm_filter(*_args, **_kwargs):
    return {
        "history_summary": "A summary.",
        "workspace_facts": [],
        "global_insights": [],
    }


def test_distillation_result_defaults():
    result = DistillationResult()

    assert result.history_summary == ""
    assert result.workspace_facts == []
    assert result.global_insights == []
    assert result.promoted_counts == {"tier1": 0, "tier2": 0, "tier3": 0}
    assert result.dropped_reasons == []


def test_memory_distiller_uses_explicit_global_path(tmp_path):
    db_path = str(tmp_path / "global.db")
    distiller = MemoryDistiller(_fake_llm_filter, global_db_path=db_path)

    assert distiller.global_db_path == db_path


def test_memory_distiller_rejects_non_callable_filter():
    with pytest.raises(TypeError, match="llm_filter must be callable"):
        MemoryDistiller(None)


def test_memory_distiller_distill_session_not_implemented():
    distiller = MemoryDistiller(_fake_llm_filter)

    with pytest.raises(NotImplementedError, match="Phase 2"):
        distiller.distill_session(workspace={}, root_path="/tmp/workspace", session_id="s1")
