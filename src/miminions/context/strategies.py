"""Per-section compaction strategies applied while building the agent context."""

from __future__ import annotations

import logging
from typing import Callable, Protocol

from miminions.memory.budget import count_tokens

logger = logging.getLogger(__name__)

_TRUNCATED_MARK = "[truncated]"


class SectionStrategy(Protocol):
    """Shrinks one context section's text to fit a token budget (never rewrites files)."""

    def compact(self, text: str, budget_tokens: int) -> str: ...


class KeepAll:
    """Leave the section untouched."""

    def compact(self, text: str, budget_tokens: int) -> str:
        return text


class TruncateLines:
    """Keep leading lines until the budget is reached; optionally clip long lines."""

    def __init__(self, max_line_chars: int | None = None):
        assert max_line_chars is None or max_line_chars > 0
        self.max_line_chars = max_line_chars

    def _clip(self, line: str) -> str:
        limit = self.max_line_chars
        if limit is None or len(line) <= limit:
            return line
        return line[: max(limit - 3, 0)] + "..."

    def compact(self, text: str, budget_tokens: int) -> str:
        assert budget_tokens > 0
        lines = [self._clip(line) for line in text.splitlines()]
        if count_tokens("\n".join(lines)) <= budget_tokens:
            return "\n".join(lines)

        kept: list[str] = []
        for line in lines:
            if count_tokens("\n".join([*kept, line, _TRUNCATED_MARK])) > budget_tokens:
                break
            kept.append(line)
        return "\n".join([*kept, _TRUNCATED_MARK])


class LLMSummary:
    """Summarise with a caller-supplied function; truncate if it fails or overshoots.

    Results are cached by (text, budget) so the model is not called on every turn.
    """

    def __init__(
        self,
        summarizer: Callable[[str, int], str],
        fallback: SectionStrategy | None = None,
    ):
        assert callable(summarizer)
        self.summarizer = summarizer
        self.fallback = fallback or TruncateLines()
        self._cache: dict[tuple[str, int], str] = {}

    def compact(self, text: str, budget_tokens: int) -> str:
        assert budget_tokens > 0
        if count_tokens(text) <= budget_tokens:
            return text
        key = (text, budget_tokens)
        if key in self._cache:
            return self._cache[key]
        try:
            summary = self.summarizer(text, budget_tokens).strip()
        except Exception as exc:
            logger.warning("LLM section summary failed, truncating: %s", exc)
            summary = ""
        if not summary or count_tokens(summary) > budget_tokens:
            summary = self.fallback.compact(text, budget_tokens)
        self._cache[key] = summary
        return summary
