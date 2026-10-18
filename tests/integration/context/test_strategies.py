"""Tests for per-section context compaction strategies."""

from __future__ import annotations

import pytest

from miminions.context.strategies import KeepAll, LLMSummary, TruncateLines
from miminions.memory.budget import count_tokens


def _lines(count: int, width: int = 40) -> str:
    return "\n".join(f"- item {i} " + "x" * width for i in range(count))


def test_keep_all_returns_text_unchanged():
    text = _lines(20)

    result = KeepAll().compact(text, 1)

    assert result == text, f"expect KeepAll leaves text unchanged, got result={result!r}, expected={text!r}"


def test_truncate_lines_is_noop_under_budget():
    text = _lines(3, width=5)

    result = TruncateLines().compact(text, 10_000)

    assert result == text, f"expect text under budget unchanged as True, got {result == text}"
    assert "[truncated]" not in result, f"expect no truncation marker under budget as True, got {result}"


def test_truncate_lines_keeps_leading_lines_and_fits_budget():
    text = _lines(50)

    result = TruncateLines().compact(text, 60)

    assert count_tokens(result) <= 60, f"expect result within 60 tokens as True, got {count_tokens(result)}"
    assert result.startswith("- item 0 "), f"expect leading line kept first as True, got {result[:20]}"
    assert result.endswith("[truncated]"), f"expect truncation marker last as True, got {result[-20:]}"
    assert "- item 49" not in result, f"expect trailing lines dropped as True, got {result}"


def test_truncate_lines_clips_long_lines():
    result = TruncateLines(max_line_chars=20).compact("y" * 200, 10_000)

    assert result == "y" * 17 + "...", f"expect long line clipped to 20 chars as {'y' * 17 + '...'}, got {result}"


def test_truncate_lines_handles_empty_text():
    result = TruncateLines().compact("", 10)

    assert result == "", f"expect empty text stays empty as '', got {result!r}"


def test_truncate_lines_rejects_non_positive_budget():
    with pytest.raises(AssertionError):
        TruncateLines().compact("abc", 0)


def test_truncate_lines_rejects_non_positive_line_limit():
    with pytest.raises(AssertionError):
        TruncateLines(max_line_chars=0)


def test_llm_summary_skips_model_when_under_budget():
    calls: list[int] = []

    def summarizer(text: str, budget: int) -> str:
        calls.append(budget)
        return "never"

    result = LLMSummary(summarizer).compact("short", 10_000)

    assert result == "short", f"expect under-budget text unchanged as 'short', got {result}"
    assert calls == [], f"expect summarizer not called as [], got {calls}"


def test_llm_summary_uses_summary_and_caches_result():
    calls: list[int] = []

    def summarizer(text: str, budget: int) -> str:
        calls.append(budget)
        return "  short summary  "

    strategy = LLMSummary(summarizer)
    text = _lines(50)

    first = strategy.compact(text, 60)
    second = strategy.compact(text, 60)

    assert first == "short summary", f"expect stripped summary as 'short summary', got {first!r}"
    assert second == first, f"expect cached result equal to first as True, got {second == first}"
    assert len(calls) == 1, f"expect summarizer called once thanks to cache as 1, got {len(calls)}"


def test_llm_summary_falls_back_when_summarizer_raises():
    def summarizer(text: str, budget: int) -> str:
        raise RuntimeError("model down")

    result = LLMSummary(summarizer).compact(_lines(50), 60)

    assert count_tokens(result) <= 60, f"expect fallback result within 60 tokens as True, got {count_tokens(result)}"
    assert result.endswith("[truncated]"), f"expect truncation fallback marker as True, got {result[-20:]}"


def test_llm_summary_falls_back_when_summary_exceeds_budget():
    def summarizer(text: str, budget: int) -> str:
        return _lines(50)

    result = LLMSummary(summarizer).compact(_lines(50), 60)

    assert count_tokens(result) <= 60, f"expect fallback result within 60 tokens as True, got {count_tokens(result)}"


def test_llm_summary_falls_back_when_summary_is_blank():
    result = LLMSummary(lambda text, budget: "   ").compact(_lines(50), 60)

    assert result.endswith("[truncated]"), f"expect blank summary replaced by truncation as True, got {result[-20:]}"


def test_llm_summary_rejects_non_callable():
    with pytest.raises(AssertionError):
        LLMSummary(None)
