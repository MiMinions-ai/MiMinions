"""Memory distiller stub — placeholder until the long-term-memory branch is merged."""

from __future__ import annotations

from typing import Any


def llm_filter(transcript: str = "", **_kwargs: Any) -> dict[str, Any]:
    """Stub context injected into the agent as its base identity prompt.

    Returns a minimal dict that seeds the agent's personality.
    Replace this with a real LLM extraction call when the memory PR lands.
    """
    return {
        "history_summary": (
            "You are MiMinions, an agentic AI assistant. "
            "Help the user with their workspace tasks. "
            "Use your available tools when relevant."
        ),
        "workspace_facts": [],
        "global_insights": [],
    }
