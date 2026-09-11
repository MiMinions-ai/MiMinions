"""Token-budget tracking and observability for the three memory tiers."""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from miminions.workspace_fs.layout import WorkspaceLayout

logger = logging.getLogger(__name__)

DEFAULT_HISTORY_BUDGET_TOKENS = 16_000
DEFAULT_MEMORY_BUDGET_TOKENS = 8_000
DEFAULT_VECTOR_MAX_ROWS = 5000

STATE_FILENAME = "BUDGET_STATE.json"

_ENCODING_NAME = "cl100k_base"
_encoding: Any = None  # lazily loaded tiktoken encoding, or False if unavailable


def count_tokens(text: str) -> int:
    """Count tokens in text, using tiktoken with a whitespace-split fallback."""
    global _encoding
    if not text:
        return 0
    if _encoding is None:
        try:
            import tiktoken

            _encoding = tiktoken.get_encoding(_ENCODING_NAME)
        except Exception as exc:  # pragma: no cover - offline/optional dep failure
            logger.warning("tiktoken unavailable, falling back to word-count estimate: %s", exc)
            _encoding = False
    if _encoding is False:
        return len(text.split())
    return len(_encoding.encode(text))


@dataclass
class MemoryBudgets:
    """Configurable token/row budgets for each memory tier."""

    history_tokens: int = DEFAULT_HISTORY_BUDGET_TOKENS
    memory_tokens: int = DEFAULT_MEMORY_BUDGET_TOKENS
    vector_max_rows: int = DEFAULT_VECTOR_MAX_ROWS


@dataclass
class TierStatus:
    """Current size vs. budget for a single tier."""

    name: str
    size_tokens: int
    budget_tokens: int

    @property
    def over_budget(self) -> bool:
        return self.size_tokens > self.budget_tokens


@dataclass
class CompactionOutcome:
    """Result of a single distillation/compaction pass, for observability."""

    tier: str
    triggered_at: str
    facts_before: int
    facts_after: int
    facts_promoted: int
    facts_dropped_duplicate: int
    size_before_tokens: int
    size_after_tokens: int
    succeeded: bool
    error: str = ""


def _state_path(root_path: str | Path) -> Path:
    layout = WorkspaceLayout.from_root(root_path)
    return layout.memory_dir / STATE_FILENAME


def get_history_size_tokens(root_path: str | Path) -> int:
    """Return current token count of HISTORY.md, or 0 if absent."""
    layout = WorkspaceLayout.from_root(root_path)
    history_file = layout.memory_dir / "HISTORY.md"
    if not history_file.exists():
        return 0
    return count_tokens(history_file.read_text(encoding="utf-8"))


def get_memory_size_tokens(root_path: str | Path) -> int:
    """Return current token count of MEMORY.md, or 0 if absent."""
    layout = WorkspaceLayout.from_root(root_path)
    memory_file = layout.memory_dir / "MEMORY.md"
    if not memory_file.exists():
        return 0
    return count_tokens(memory_file.read_text(encoding="utf-8"))


def check_pressure(
    root_path: str | Path, budgets: MemoryBudgets | None = None
) -> dict[str, TierStatus]:
    """Return size/budget status for HISTORY.md and MEMORY.md."""
    if budgets is None:
        budgets = MemoryBudgets()
    return {
        "history": TierStatus("history", get_history_size_tokens(root_path), budgets.history_tokens),
        "memory": TierStatus("memory", get_memory_size_tokens(root_path), budgets.memory_tokens),
    }


def load_state(root_path: str | Path) -> dict[str, Any]:
    """Load the persisted budget/compaction observability state."""
    path = _state_path(root_path)
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError) as exc:
        logger.warning("Failed to read %s: %s", path, exc)
        return {}


def record_state(
    root_path: str | Path,
    budgets: MemoryBudgets,
    statuses: dict[str, TierStatus],
    outcome: CompactionOutcome | None = None,
) -> Path:
    """Persist tier budgets, current sizes, and the last compaction outcome."""
    state = load_state(root_path)
    state["budgets"] = asdict(budgets)
    state["sizes"] = {
        name: {"size_tokens": status.size_tokens, "budget_tokens": status.budget_tokens}
        for name, status in statuses.items()
    }
    state["checked_at"] = datetime.now(timezone.utc).isoformat()

    if outcome is not None:
        history = state.get("compaction_history", [])
        history.append(asdict(outcome))
        state["compaction_history"] = history[-20:]
        state["last_compaction"] = asdict(outcome)

    path = _state_path(root_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return path


def enforce_history_budget(
    root_path: str | Path, budgets: MemoryBudgets | None = None
) -> CompactionOutcome:
    """Trim the oldest HISTORY.md lines so the file fits its token budget.

    HISTORY.md is append-only raw log data, so pressure relief here is
    truncation (oldest first) rather than promotion/dedup.
    """
    if budgets is None:
        budgets = MemoryBudgets()

    layout = WorkspaceLayout.from_root(root_path)
    history_file = layout.memory_dir / "HISTORY.md"
    triggered_at = datetime.now(timezone.utc).isoformat()

    if not history_file.exists():
        size = 0
        lines_before = 0
    else:
        data = history_file.read_text(encoding="utf-8")
        size = count_tokens(data)
        lines_before = len(data.splitlines())

    outcome = CompactionOutcome(
        tier="history",
        triggered_at=triggered_at,
        facts_before=lines_before,
        facts_after=lines_before,
        facts_promoted=0,
        facts_dropped_duplicate=0,
        size_before_tokens=size,
        size_after_tokens=size,
        succeeded=True,
    )

    if size <= budgets.history_tokens:
        outcome.error = "no_pressure: under budget, no trim needed"
        return outcome

    lines = history_file.read_text(encoding="utf-8").splitlines(keepends=True)
    while lines and count_tokens("".join(lines)) > budgets.history_tokens:
        lines.pop(0)
    trimmed = "".join(lines)
    history_file.write_text(trimmed, encoding="utf-8")

    outcome.facts_after = len(trimmed.splitlines())
    outcome.size_after_tokens = count_tokens(trimmed)
    return outcome
