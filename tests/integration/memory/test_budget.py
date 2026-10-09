"""Tests for memory-tier byte budgets and pressure observability."""

from __future__ import annotations

import json
from pathlib import Path

from miminions.memory.budget import (
    MemoryBudgets,
    check_pressure,
    enforce_history_budget,
    get_history_size_tokens,
    get_memory_size_tokens,
    load_state,
    record_state,
)
from miminions.memory.md_store import append_history, write_memory
from miminions.workspace_fs.bootstrap import init_workspace


def test_check_pressure_reports_under_budget_for_fresh_workspace(tmp_path: Path):
    init_workspace(tmp_path)
    budgets = MemoryBudgets(history_tokens=1024, memory_tokens=1024)

    statuses = check_pressure(tmp_path, budgets)

    assert statuses["history"].over_budget is False, f"expect fresh HISTORY.md under budget as False, got {statuses['history'].over_budget}"
    assert statuses["memory"].over_budget is False, f"expect fresh MEMORY.md under budget as False, got {statuses['memory'].over_budget}"


def test_check_pressure_detects_threshold_crossing(tmp_path: Path):
    init_workspace(tmp_path)
    write_memory(tmp_path, "# Memory\n\n" + " ".join(f"word{i}" for i in range(200)) + "\n")
    budgets = MemoryBudgets(memory_tokens=50)

    statuses = check_pressure(tmp_path, budgets)

    assert statuses["memory"].over_budget is True, f"expect MEMORY.md exceeding 50-token budget over_budget as True, got {statuses['memory'].over_budget}"
    assert statuses["memory"].size_tokens == get_memory_size_tokens(tmp_path), f"expect size_tokens matches get_memory_size_tokens as {get_memory_size_tokens(tmp_path)}, got {statuses['memory'].size_tokens}"


def test_record_state_persists_budgets_sizes_and_compaction(tmp_path: Path):
    init_workspace(tmp_path)
    budgets = MemoryBudgets(history_tokens=1024, memory_tokens=1024)
    statuses = check_pressure(tmp_path, budgets)

    record_state(tmp_path, budgets, statuses)
    state = load_state(tmp_path)

    assert state["budgets"]["memory_tokens"] == 1024, f"expect persisted memory_tokens budget as 1024, got {state['budgets']['memory_tokens']}"
    assert "sizes" in state, f"expect 'sizes' key present in state as True, got {'sizes' in state}"
    assert "checked_at" in state, f"expect 'checked_at' key present in state as True, got {'checked_at' in state}"

    state_file = tmp_path / "memory" / "BUDGET_STATE.json"
    assert state_file.exists(), f"expect BUDGET_STATE.json written to disk as True, got {state_file.exists()}"
    on_disk = json.loads(state_file.read_text(encoding="utf-8"))
    assert on_disk == state, f"expect on-disk state matches load_state result as {state}, got {on_disk}"


def test_enforce_history_budget_is_noop_under_budget(tmp_path: Path):
    init_workspace(tmp_path)
    append_history(tmp_path, "first entry")
    budgets = MemoryBudgets(history_tokens=10_000)

    outcome = enforce_history_budget(tmp_path, budgets)

    assert outcome.succeeded is True, f"expect no-op enforcement to report succeeded as True, got {outcome.succeeded}"
    assert outcome.facts_before == outcome.facts_after, f"expect no lines trimmed when under budget as {outcome.facts_before}, got {outcome.facts_after}"


def test_enforce_history_budget_trims_oldest_lines_when_over_budget(tmp_path: Path):
    init_workspace(tmp_path)
    for i in range(20):
        append_history(tmp_path, f"session {i} did something notable and lengthy for size")
    budgets = MemoryBudgets(history_tokens=200)

    outcome = enforce_history_budget(tmp_path, budgets)

    assert outcome.succeeded is True, f"expect trimming to report succeeded as True, got {outcome.succeeded}"
    assert get_history_size_tokens(tmp_path) <= 200, f"expect HISTORY.md size within 200-token budget after trim, got {get_history_size_tokens(tmp_path)}"
    remaining = (tmp_path / "memory" / "HISTORY.md").read_text(encoding="utf-8")
    assert "session 19" in remaining, f"expect most recent entry 'session 19' preserved after trim as True, got 'session 19' in remaining: {'session 19' in remaining}"
    assert "session 0 " not in remaining, f"expect oldest entry 'session 0' dropped after trim as True, got 'session 0 ' in remaining: {'session 0 ' in remaining}"
