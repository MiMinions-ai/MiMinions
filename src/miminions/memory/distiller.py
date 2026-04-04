"""Session distillation scaffolding for hierarchical memory tiers."""

from dataclasses import dataclass, field
from typing import Any, Callable

from .sqlite import get_global_memory_db_path


@dataclass
class DistillationResult:
    """Structured outcome for a single session distillation run."""

    history_summary: str = ""
    workspace_facts: list[str] = field(default_factory=list)
    global_insights: list[dict[str, Any]] = field(default_factory=list)
    promoted_counts: dict[str, int] = field(
        default_factory=lambda: {"tier1": 0, "tier2": 0, "tier3": 0}
    )
    dropped_reasons: list[str] = field(default_factory=list)


class MemoryDistiller:
    """Scaffold for extracting durable memory from session transcripts."""

    def __init__(self, llm_filter: Callable[..., dict[str, Any]], global_db_path: str | None = None):
        if not callable(llm_filter):
            raise TypeError("llm_filter must be callable")
        self.llm_filter = llm_filter
        self.global_db_path = global_db_path or get_global_memory_db_path(create_dir=True)

    def distill_session(self, workspace: Any, root_path: str, session_id: str) -> DistillationResult:
        """Distill a single session into tiered memory outputs.

        Phase 1 provides API shape only; full implementation lands in Phase 2.
        """
        raise NotImplementedError("MemoryDistiller.distill_session will be implemented in Phase 2")
