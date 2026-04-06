# Memory Evolution Plan: Minimal Three-Tier Memory

## Goal

Keep memory simple and markdown-first.

1. Tier 1: session log in `sessions/*.jsonl` plus one summary line in `memory/HISTORY.md`.
2. Tier 2: workspace truth in `memory/MEMORY.md`.
3. Tier 3: global SQLite index in `~/.miminions/global_memory.db` for reusable cross-workspace context.

The future LLM does most of the selection work. The system only does lightweight plumbing.

## Core Principles

1. Local markdown is the source of truth.
2. SQLite is an optional global index layer, not a replacement for markdown.
3. Distiller should be permissive and small.
4. On failure, skip Tier 3 and continue; chat flow must never break.

## Minimal Distiller Contract

Input from LLM (per session):

```json
{
  "history_summary": "one-line summary",
  "workspace_facts": ["fact 1", "fact 2"],
  "global_insights": ["insight 1", "insight 2"]
}
```

Notes:

1. Keep schema flexible: missing fields default to empty.
2. Accept `global_insights` as simple strings.
3. No complex deterministic semantic filtering in application code.
4. Minimal dedupe only: exact normalized text dedupe.

## Tier Behavior

### Tier 1 (History)

1. Append `history_summary` to `memory/HISTORY.md` if non-empty.

### Tier 2 (Workspace Memory)

1. Upsert `workspace_facts` into `memory/MEMORY.md` under `## Project Facts`.

### Tier 3 (Global SQLite)

1. Store each global insight as plain text in SQLite.
2. Attach minimal provenance metadata:
   - `workspace_id`
   - `workspace_name`
   - `session_id`
   - `source="distiller"`
   - `created_at`

No additional hard-coded categories, confidence gates, or rule-heavy heuristics are required in app logic.

## Source-of-Truth Rule

1. Never overwrite `memory/MEMORY.md` from SQLite.
2. Global memory is read-only context injection into prompts.
3. If global DB is missing or unavailable, continue with local memory only.

## Simplified Delivery Plan

## Step 0: Refactor Current Phase 2 to Minimal Mode

**Commit message**: `refactor(memory): simplify distiller to llm-first minimal pipeline`

**Files**:

- `src/miminions/memory/distiller.py`
- `tests/test_distiller.py`

**Scope**:

1. Remove strict schema enforcement and rule-heavy filtering.
2. Normalize input with permissive defaults.
3. Keep only lightweight dedupe and empty-string checks.
4. Persist Tier 3 as plain insights with provenance metadata.
5. Keep `DistillationResult`, but reduce emphasis on granular drop reasons.

**Done when**:

1. Distiller is notably smaller and easier to reason about.
2. Missing fields and partial LLM output do not fail the run.
3. Tier 1 and Tier 2 behavior remains unchanged.

## Step 1: Runtime Hook

**Commit message**: `feat(runtime): run distiller on chat exit`

**Files**:

- `src/miminions/interface/cli/chat.py`
- `tests/cli/test_chat.py`

**Scope**:

1. Run distillation once on session exit (`quit`, `exit`, EOF, Ctrl+C).
2. Distiller errors are warnings only.

**Done when**:

1. Chat exits cleanly in all paths.
2. Distillation never blocks completion.

## Step 2: Global Context Injection

**Commit message**: `feat(context): inject global sqlite insights`

**Files**:

- `src/miminions/agent/context_builder.py`
- `tests/test_context_builder.py`

**Scope**:

1. Read top-k global entries from SQLite.
2. Inject as `## Global Knowledge` before local `## Memory`.
3. Gracefully skip if DB unavailable.

**Done when**:

1. Context builds with or without SQLite.
2. Ordering is deterministic.

## Step 3: Minimal Hardening + Docs

**Commit message**: `test+docs(memory): document minimal global memory model`

**Files**:

- `README.md`
- `tests/test_distiller.py`
- `tests/test_context_builder.py`
- `src/miminions/memory/MEMORY_EVOLUTION_PLAN.md`

**Scope**:

1. Add tests for empty session and SQLite unavailability.
2. Document markdown-first + SQLite-index contract.
3. Document a small config surface (`top_k`, optional Tier 3 off switch).

**Done when**:

1. Behavior is clear without reading implementation internals.
2. Runtime degrades gracefully on all memory-layer failures.

## Default Operating Stance

1. Let the LLM decide what is reusable.
2. Keep app-side memory logic thin.
3. Prefer simple storage and retrieval over heavy in-code curation.