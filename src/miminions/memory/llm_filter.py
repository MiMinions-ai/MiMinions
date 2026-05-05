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
    import asyncio
    import json
    from pydantic_ai import Agent

    def llm_filter(transcript: str, **_kwargs: Any) -> dict[str, Any]:
        empty: dict[str, Any] = {
            "history_summary": "",
            "workspace_facts": [],
            "global_insights": [],
        }

        if not transcript.strip():
            return empty

        prompt = EXTRACTION_PROMPT.format(transcript=transcript)
        extraction_agent = Agent(
            model=model,
            instructions="Extract memory from transcripts. Respond with JSON only.",
        )

        async def _run() -> str:
            result = await extraction_agent.run(prompt)
            return result.output if hasattr(result, "output") else str(result.data)

        # Bridge async → sync safely regardless of whether a loop is running.
        try:
            loop = asyncio.get_event_loop()
        except RuntimeError:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)

        if loop.is_running():
            # Already inside an event loop (e.g. inside the async chat loop).
            # Use a new thread with its own event loop to avoid nesting.
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(asyncio.run, _run())
                raw = future.result()
        else:
            raw = loop.run_until_complete(_run())

        raw = raw.strip()

        # Strip markdown fences if the model wraps its JSON in ```json ... ```.
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.strip().startswith("```")
            ).strip()

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            # Partial extraction: preserve summary even if JSON is malformed.
            return {
                "history_summary": raw[:500],
                "workspace_facts": [],
                "global_insights": [],
            }

        if not isinstance(payload, dict):
            return empty

        return {
            "history_summary": str(payload.get("history_summary", "")).strip(),
            "workspace_facts": payload.get("workspace_facts", []),
            "global_insights": payload.get("global_insights", []),
        }

    return llm_filter
