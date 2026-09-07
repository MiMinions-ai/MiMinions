# 0001. pydantic-ai as the agent foundation

Date: 2026-02-01
Status: reconstructed (2026-09-01)

## Context

The project restarted in mid-2025 as an agentic framework. Something had to own
the model-call loop, tool dispatch, and structured output. The options were to
hand-roll it against provider SDKs, adopt a large framework, or adopt a thin
typed library.

The commit `Adjusted Pydantic package to Pydantic_AI for LLM support` marks the
switch. Plain `pydantic` was already a dependency for models, so the move was
incremental rather than a rewrite.

## Decision

Build `Minion` on `pydantic-ai`, pinned `>=1.0.0,<2.0.0`. Provider selection is
funnelled through a local `ModelFactory` rather than exposing pydantic-ai's
model classes to callers.

## Consequences

- The agent loop, retries, and tool-calling protocol are largely inherited, so
  the `agent` subpackage stays small: four files.
- The major-version ceiling is deliberate. A CI break on 2026-06-26 (`fix(ci):
  use OpenAIChatModel, pin pydantic-ai`) showed the API surface moves under us,
  so the pin is load-bearing, not cosmetic.
- `ModelFactory` is the seam that keeps that churn from reaching callers.
  Provider handling should stay behind it.
- Anything pydantic-ai cannot express has to be worked around rather than
  reimplemented, since replacing it now would mean rewriting the agent layer.
