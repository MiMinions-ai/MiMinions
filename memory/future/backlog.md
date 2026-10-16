# Backlog

Candidate work. Each item carries a **trigger**: the condition that makes it
worth doing *now*. An item with no trigger is not ready to be picked up.

Ordered by readiness, not priority.

## Ready

### Gate the integration branch in CI

CI runs only on `main`, so merges into `development` are ungated.

- Trigger: already true. Every PR into `development` is unverified today.
- Size: one line in `.github/workflows/python-app.yml`.
- See `open-questions.md` OQ-7 for the trigger-scope options.

### Add memory commands to the CLI

`memory-attach`, `memory-store`, `memory-recall`, `memory-update`,
`memory-delete`, `ingest-document`. Marked in `src/miminions/cli/agent.py`.

- Trigger: already true. The capability exists and is CLI-inaccessible.
- Constraint: must degrade cleanly when the `sqlite` extra is absent (ADR 0004).
- Size: moderate. Six commands over an existing backend.

### Make the chat agent description configurable per workspace

`cli/chat.py` hardcodes the agent description string.

- Trigger: a user wants distinct agent personas per workspace.
- Size: small.

### Cache context memory dedupe

`ContextBuilder.build` runs semantic dedupe on MEMORY.md every build, loading
the embedding model and embedding all bullets each turn.

- Trigger: per-turn latency from context building becomes noticeable, or
  `fastembed` model download fails in a user environment.
- Options: cache by text hash, or make semantic dedupe opt-in (exact by default).
- Size: small.

### Decide the fate of HISTORY.md

HISTORY.md is written by the distiller but never read into the agent context.
`enforce_history_budget` and `MemoryBudgets.history_tokens` are only used by
tests; the distiller no longer trims history, so the file grows unbounded.

- Trigger: a user reports a large HISTORY.md, or history is wanted as agent context.
- Options: add a budgeted `history` section to `ContextBuilder` and re-wire
  trimming; or remove the unused trimming code.
- Size: small to moderate.

### Memory compaction cleanups

- Narrow the broad `except Exception` around vector promotion in
  `memory/compaction.py`.
- Bound `LLMSummary._cache` in `context/strategies.py` (unbounded, keyed by
  full section text).
- `MemoryBudgets.vector_max_rows` is defined but never enforced.

- Trigger: any of these causes a bug report, or the vector tier gets a size policy.
- Size: small each.

## Blocked on a decision

### Widen the ruff rule set

ADR 0005 chose a narrow blocking gate. The stylistic debt beneath it is
untracked.

- Trigger: someone is willing to absorb one large mechanical diff, or to commit
  to adding rule families incrementally.
- Now cheaper than before: config lives in `pyproject.toml`, so widening is a
  one-line change.
- Blocked on: appetite for churn, not on any technical obstacle.

### Integrate or remove `workflow`

Models, controller, and trace types exist; no command group ships; nothing
imports it.

- Trigger: either a concrete use case for workflow tracing, or a release where
  tree comprehension matters more than optionality.
- Blocked on: deciding whether workflow tracing is part of the product.

### Integrate or remove `user`

A dataclass and a stub controller, with no internal callers. 0.3.0 removed the
"complex user authentication and validation systems" that presumably used it.

- Trigger: real authentication work begins (see below), or a cleanup pass.
- Blocked on: the same question as ADR 0006.

### Implement real authentication

`require_auth` is an identity decorator. `TODO(auth)` markers sit at every call
site in `cli/task.py` and `cli/execution.py`.

- Trigger: account-backed features become a product goal.
- Constraint: doing this should reverse the `core -> cli` import cycle by moving
  the predicates down into `core`. See ADR 0006.
- Blocked on: product direction. Not a technical question.

## Not ready

### Reconsider the setuptools build backend

ADR 0003 kept setuptools by inertia rather than by choice.

- Trigger: none. It works, and switching backends has real risk with no current
  payoff. Recorded only so the inertia is visible.
