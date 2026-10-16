"""LLM extraction filter for session distillation."""

import json
from typing import Any, Callable

EXTRACTION_PROMPT = """\
You are a memory extraction system. Read the conversation transcript below and extract
the following, responding ONLY with valid JSON — no markdown, no explanation:

{{
  "history_summary": "<one or two sentences summarising what happened in this session>",
  "workspace_facts": ["<concrete fact about the project or workspace>", ...],
  "global_insights": ["<general insight that applies across workspaces>", ...]
}}

Rules:
- history_summary must not be empty.
- workspace_facts are project-specific: file names, decisions, bugs, features.
- global_insights are reusable patterns: best practices, user preferences, recurring issues.
- Return empty lists if there is nothing to extract. Don't try to force extra information.
- Respond with JSON only.

Transcript:
{transcript}
"""


def _parse_json_response(raw: str) -> tuple[dict[str, Any] | None, str]:
    """Strip markdown fences and parse JSON; returns (dict, cleaned_raw) or (None, cleaned_raw)."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = "\n".join(
            line for line in raw.splitlines()
            if not line.strip().startswith("```")
        ).strip()
    try:
        result = json.loads(raw)
        return (result if isinstance(result, dict) else None), raw
    except json.JSONDecodeError:
        return None, raw


COMPACTION_PROMPT = """\
You are compacting a long-term memory file. Rewrite the facts below so the whole
file fits within about {target_tokens} tokens (roughly {target_chars} characters).

Rules:
- Merge duplicates and near-duplicates; drop superseded or trivial facts.
- Keep concrete details (names, paths, decisions); do not invent anything.
- Keep each fact short and keep its section.
- Respond ONLY with JSON: {{"facts": [{{"section": "<heading>", "fact": "<text>"}}, ...]}}

Facts:
{facts}
"""


def _run_agent_sync(model: Any, instructions: str, prompt: str) -> str:
    """Run a one-shot pydantic_ai agent from sync code, even inside a running loop."""
    import asyncio
    from pydantic_ai import Agent

    agent = Agent(model=model, instructions=instructions)

    async def _run() -> str:
        result = await agent.run(prompt)
        return result.output if hasattr(result, "output") else str(result.response)

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_run())

    import concurrent.futures
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _run()).result()


def create_llm_compactor(
    model: Any,
) -> Callable[[list[tuple[str, str]], int], list[tuple[str, str]]]:
    """Return a ``compactor(facts, target_tokens)`` that rewrites facts via an LLM.

    Raises ValueError when the response is not the expected JSON, so callers
    can fall back to non-LLM compaction.
    """

    def compactor(facts: list[tuple[str, str]], target_tokens: int) -> list[tuple[str, str]]:
        payload = json.dumps([{"section": h, "fact": t} for h, t in facts])
        prompt = COMPACTION_PROMPT.format(
            target_tokens=target_tokens, target_chars=target_tokens * 4, facts=payload
        )
        raw = _run_agent_sync(
            model, "Compact memory facts. Respond with JSON only.", prompt
        )
        parsed, _ = _parse_json_response(raw)
        items = parsed.get("facts") if parsed else None
        if not isinstance(items, list):
            raise ValueError("compactor response missing 'facts' list")
        result: list[tuple[str, str]] = []
        for item in items:
            if not isinstance(item, dict):
                continue
            fact = str(item.get("fact", "")).strip()
            if fact:
                result.append((str(item.get("section", "General")).strip() or "General", fact))
        return result

    return compactor


def create_llm_filter(model: Any) -> Callable[..., dict[str, Any]]:
    """Return a real LLM-backed ``llm_filter`` callable for ``MemoryDistiller``.

    The returned function is **synchronous** so it can be invoked from inside
    the sync ``distill_session()`` pipeline (which runs in a ``finally`` block).
    The pydantic_ai call is async under the hood; we bridge it with
    ``asyncio.run()`` when there is no running loop, or a thread-pool when one
    already exists but cannot be nested.

    Args:
        model: Any pydantic_ai-compatible model (e.g. ``OpenAIModel``).

    Returns:
        A synchronous callable with the signature
        ``(transcript, **kwargs) -> dict[str, Any]``.
    """
    def llm_filter(transcript: str, **_kwargs: Any) -> dict[str, Any]:
        empty: dict[str, Any] = {
            "history_summary": "",
            "workspace_facts": [],
            "global_insights": [],
        }

        if not transcript.strip():
            return empty

        prompt = EXTRACTION_PROMPT.format(transcript=transcript)
        raw = _run_agent_sync(
            model, "Extract memory from transcripts. Respond with JSON only.", prompt
        )

        payload, raw = _parse_json_response(raw)
        if payload is None:
            return {
                "history_summary": raw[:500],
                "workspace_facts": [],
                "global_insights": [],
            }

        return {
            "history_summary": str(payload.get("history_summary", "")).strip(),
            "workspace_facts": payload.get("workspace_facts", []),
            "global_insights": payload.get("global_insights", []),
        }

    return llm_filter
