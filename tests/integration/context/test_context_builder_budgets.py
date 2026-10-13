"""Tests for ContextBuilder per-section budgets and strategies."""

from __future__ import annotations

from pathlib import Path

import pytest

from miminions.context import ContextBuilder
from miminions.context.strategies import TruncateLines
from miminions.memory.md_store import write_memory
from miminions.workspace_fs.bootstrap import init_workspace


class _Workspace:
    id = "ws_1"
    name = "Budget Workspace"
    nodes: list = []
    rules: list = []
    state: dict = {}

    def __init__(self, root_path: str):
        self.root_path = root_path


def _build(tmp_path: Path, **kwargs) -> str:
    return ContextBuilder(global_top_k=0, **kwargs).build(_Workspace(str(tmp_path)), tmp_path)


def _seed_long_memory(tmp_path: Path) -> None:
    init_workspace(tmp_path)
    facts = "\n".join(f"- memory fact {i} " + "z" * 60 for i in range(80))
    write_memory(tmp_path, f"# Memory\n\n{facts}\n")


def test_context_is_unchanged_without_budgets(tmp_path):
    _seed_long_memory(tmp_path)

    plain = _build(tmp_path)
    with_empty = _build(tmp_path, strategies={"memory": TruncateLines()}, budgets={})

    def _strip_time(text: str) -> list[str]:
        return [line for line in text.splitlines() if not line.startswith("- current_time_utc")]

    assert _strip_time(with_empty) == _strip_time(plain), "expect identical context when no budgets are set"
    assert "memory fact 79" in with_empty, f"expect full memory kept without a budget as True, got {'memory fact 79' in with_empty}"


def test_memory_section_is_truncated_when_over_budget(tmp_path):
    _seed_long_memory(tmp_path)

    context = _build(tmp_path, strategies={"memory": TruncateLines()}, budgets={"memory": 100})

    assert "memory fact 0" in context, f"expect leading memory fact kept as True, got {'memory fact 0' in context}"
    assert "memory fact 79" not in context, f"expect trailing memory fact dropped as True, got {'memory fact 79' in context}"
    assert "[truncated]" in context, f"expect truncation marker present as True, got {'[truncated]' in context}"
    assert "## Workspace Graph Summary" in context, f"expect later sections still rendered as True, got {'## Workspace Graph Summary' in context}"


def test_budget_without_strategy_leaves_section_intact(tmp_path):
    _seed_long_memory(tmp_path)

    context = _build(tmp_path, budgets={"memory": 10})

    assert "memory fact 79" in context, f"expect budget without a strategy to keep text as True, got {'memory fact 79' in context}"


def test_identity_and_tool_boundary_are_never_compacted(tmp_path):
    _seed_long_memory(tmp_path)

    context = _build(tmp_path, strategies={"memory": TruncateLines()}, budgets={"memory": 5})

    assert "workspace_name: Budget Workspace" in context, f"expect identity kept as True, got {context[:200]}"
    assert "## Tool Boundary" in context, f"expect tool boundary kept as True, got {'## Tool Boundary' in context}"


def test_compaction_does_not_rewrite_memory_file(tmp_path):
    _seed_long_memory(tmp_path)
    before = (tmp_path / "memory" / "MEMORY.md").read_text(encoding="utf-8")

    _build(tmp_path, strategies={"memory": TruncateLines()}, budgets={"memory": 50})

    after = (tmp_path / "memory" / "MEMORY.md").read_text(encoding="utf-8")
    assert after == before, "expect MEMORY.md on disk untouched by build-time compaction"


@pytest.mark.parametrize("key", ["identity", "tool_boundary", "bogus"])
def test_unknown_section_in_budgets_is_rejected(key):
    with pytest.raises(ValueError, match="Unknown context sections"):
        ContextBuilder(budgets={key: 10})


def test_unknown_section_in_strategies_is_rejected():
    with pytest.raises(ValueError, match="Unknown context sections"):
        ContextBuilder(strategies={"bogus": TruncateLines()})
