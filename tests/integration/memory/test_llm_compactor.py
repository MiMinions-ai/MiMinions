"""Tests for the LLM compactor factory and its response parsing."""

from __future__ import annotations

import json

import pytest

from miminions.memory import llm_filter as llm_filter_module
from miminions.memory.llm_filter import create_llm_compactor

_FACTS = [("Project Facts", "uses pytest"), ("Project Facts", "tests run with pytest")]


def _patch_response(monkeypatch, response: str, seen: list[str] | None = None):
    def fake_run(model, instructions, prompt):
        if seen is not None:
            seen.append(prompt)
        return response

    monkeypatch.setattr(llm_filter_module, "_run_agent_sync", fake_run)


def test_compactor_parses_facts_and_includes_budget_in_prompt(monkeypatch):
    seen: list[str] = []
    payload = {"facts": [{"section": "Project Facts", "fact": "uses pytest"}]}
    _patch_response(monkeypatch, json.dumps(payload), seen)

    result = create_llm_compactor(object())(_FACTS, 100)

    assert result == [("Project Facts", "uses pytest")], f"expect parsed facts as [('Project Facts','uses pytest')], got {result}"
    assert "100 tokens" in seen[0], f"expect prompt states the token target as True, got {seen[0][:200]}"
    assert "tests run with pytest" in seen[0], f"expect prompt includes the input facts as True, got {seen[0][:200]}"


def test_compactor_accepts_markdown_fenced_json(monkeypatch):
    payload = '```json\n{"facts": [{"section": "S", "fact": "x"}]}\n```'
    _patch_response(monkeypatch, payload)

    result = create_llm_compactor(object())(_FACTS, 100)

    assert result == [("S", "x")], f"expect fenced JSON parsed as [('S','x')], got {result}"


def test_compactor_skips_blank_and_malformed_items_and_defaults_section(monkeypatch):
    payload = {"facts": [{"fact": "kept"}, {"section": "S", "fact": "  "}, "not-a-dict", {"section": "", "fact": "also"}]}
    _patch_response(monkeypatch, json.dumps(payload))

    result = create_llm_compactor(object())(_FACTS, 100)

    assert result == [("General", "kept"), ("General", "also")], f"expect blank/malformed items skipped and section defaulted, got {result}"


@pytest.mark.parametrize("response", ["not json at all", "[1, 2]", '{"other": []}', '{"facts": "nope"}'])
def test_compactor_raises_on_invalid_response(monkeypatch, response):
    _patch_response(monkeypatch, response)

    with pytest.raises(ValueError, match="missing 'facts' list"):
        create_llm_compactor(object())(_FACTS, 100)
