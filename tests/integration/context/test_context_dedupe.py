"""Duplicates are dropped from the built context only, never from MEMORY.md."""

from __future__ import annotations

import sys
from types import SimpleNamespace

import pytest

from miminions.context.context_builder import ContextBuilder
from miminions.memory.md_store import read_memory, upsert_memory_section
from miminions.workspace_fs.bootstrap import init_workspace


@pytest.fixture(autouse=True)
def _no_real_embedding_model(monkeypatch):
    class _Unavailable:
        def __init__(self, model_name: str):
            raise RuntimeError("model unavailable")

    monkeypatch.setitem(sys.modules, "fastembed", SimpleNamespace(TextEmbedding=_Unavailable))


def test_context_drops_duplicate_facts_but_memory_file_keeps_them(tmp_path):
    init_workspace(tmp_path)
    upsert_memory_section(tmp_path, "Facts", ["uses pytest", "Uses Pytest", "uses black"])

    context = ContextBuilder(global_top_k=0).build({"id": "ws"}, tmp_path)

    assert context.casefold().count("- uses pytest") == 1, f"expect one copy of duplicate fact in context as 1, got {context}"
    assert "- uses black" in context, f"expect unique fact kept in context as True, got {context}"
    assert read_memory(tmp_path).casefold().count("- uses pytest") == 2, "expect both duplicates still in MEMORY.md as 2"
