# Memory Evolution Plan: Three-Tier Hierarchical Memory

## Objective

Introduce a three-tier memory model where:

1. Tier 1 is the session log (`sessions/*.jsonl`) with a one-line summary promoted into `memory/HISTORY.md`.
2. Tier 2 is local workspace memory (`memory/MEMORY.md`) and remains the source of truth for project-specific knowledge.
3. Tier 3 is global memory (`~/.miminions/global_memory.db`) powered by `SQLiteMemory` and stores only high-signal, cross-workspace insights.

The design must preserve local markdown ownership while using SQLite as a global index/brain.

## Current State (Scanned)

### Prompt assembly

- `src/miminions/agent/context_builder.py` builds a single context string.
- It currently injects prompt files and local markdown memory (`read_memory(root)`), but has no global memory section.

### Workspace and paths

- Workspace model/manager is in `src/miminions/core/workspace.py` (not `src/miminions/workspace.py`).
- Workspace objects expose `id`, `name`, `root_path`, `nodes`, `rules`, and `state` used by context assembly.
- Canonical workspace directories are defined in `src/miminions/workspace_fs/layout.py` (`memory/`, `sessions/`, etc.).

### Markdown memory

- `src/miminions/memory/md_store.py` already provides:
  - `append_history()`
  - `upsert_memory_section()`
  - `read_memory()` / `write_memory()`
- These functions are enough to support Tier 1 and Tier 2 promotions.

### Session lifecycle

- `src/miminions/interface/cli/chat.py` creates/uses `JsonlSessionStore`, appends `user` and `assistant` records, and exits on `quit`, `exit`, `EOFError`, or `KeyboardInterrupt`.
- No post-session distillation hook currently exists.

### SQLite memory

- `src/miminions/memory/sqlite.py` already supports vector storage, metadata, and search methods.
- Default DB path is package-local today; Tier 3 requires canonical global path: `~/.miminions/global_memory.db`.

## Target Architecture

## Tier 1: Session Log and History

- Session JSONL remains append-only raw truth for the current conversation.
- On session exit, distiller writes exactly one concise summary line into `memory/HISTORY.md`.
- Summary format: one sentence, action-focused, no speculation.

## Tier 2: Workspace Memory (Source of Truth)

- Distiller updates `memory/MEMORY.md` with stable, project-specific facts.
- Facts are grouped in explicit sections (for example: `## Project Facts`, `## Workspace Preferences`).
- Use `upsert_memory_section()` to keep updates idempotent and readable.

## Tier 3: Global SQLite Memory (Cross-Workspace Brain)

- Distiller extracts universal insights and writes them to `~/.miminions/global_memory.db` via `SQLiteMemory`.
- Accepted insight classes:
  - User preferences
  - Universal coding standards
  - Cross-project achievements/patterns
- Rejected content:
  - Session chatter
  - Workspace-only implementation details
  - Temporary plans, unresolved questions, low-confidence statements

## No-Code-Duplicate Rule (Source of Truth Contract)

1. Local markdown files stay authoritative for workspace knowledge.
2. Tier 3 is an index/aggregation layer, not a replacement for local markdown.
3. Global entries must keep provenance metadata (`workspace_id`, `workspace_name`, `session_id`, timestamps, category).
4. Global-to-local sync is read-only context injection; never overwrite local markdown from global DB.

## Phased Delivery Plan (One Commit Per Phase)

This section converts the design into four commits total, exactly one commit per phase.

## Phase 1: Foundations

**Commit message**: `feat(memory): add global memory foundations`

**Files**:

- `src/miminions/memory/sqlite.py`
- `src/miminions/memory/distiller.py`
- `src/miminions/memory/__init__.py`
- `tests/test_sqlite_memory.py`
- `tests/test_distiller.py`

**Scope**:

1. Add canonical global DB path helper: `~/.miminions/global_memory.db`.
2. Ensure parent directory creation is handled safely.
3. Scaffold `MemoryDistiller` and `DistillationResult` API.
4. Export distiller entry points from memory package.
5. Add baseline tests for helper behavior and distiller schema/initialization.

**Done when**:

1. Global path helper and backward compatibility tests pass.
2. Distiller module is importable from package root.
3. Baseline memory and distiller tests are green.

## Phase 2: Distillation Pipeline

**Commit message**: `feat(memory): implement distillation pipeline and promotion gates`

**Files**:

- `src/miminions/memory/distiller.py`
- `tests/test_distiller.py`

**Scope**:

1. Load transcript from `JsonlSessionStore.iter_messages(session_id)` and compact it.
2. Validate strict LLM extraction schema (`history_summary`, `workspace_facts`, `global_insights`).
3. Apply deterministic filters (confidence threshold, durability, actionability, dedupe).
4. Promote accepted entries:
   - Tier 1: `append_history(root_path, history_summary)`
   - Tier 2: `upsert_memory_section(...)`
   - Tier 3: `SQLiteMemory.create(text, metadata=...)`
5. Return `DistillationResult` with promoted/dropped counts and reasons.

**Done when**:

1. Invalid/malformed LLM output is rejected with explicit reasons.
2. Missing/empty sessions are handled gracefully.
3. One-line history and workspace memory updates are written correctly.
4. Only high-confidence reusable global insights are persisted.

## Phase 3: Runtime Integration

**Commit message**: `feat(runtime): wire chat distillation and global context injection`

**Files**:

- `src/miminions/interface/cli/chat.py`
- `src/miminions/agent/context_builder.py`
- `tests/cli/test_chat.py`
- `tests/test_context_builder.py`

**Scope**:

1. Wrap chat REPL in `try/finally` and trigger distillation on exit paths.
2. Ensure distiller failures are logged as warnings and do not break chat completion.
3. Add global insight retrieval in context assembly with graceful fallback.
4. Inject `## Global Knowledge` before `## Memory`.

**Done when**:

1. Distiller runs once per exiting session (`quit`, `exit`, EOF, Ctrl+C).
2. Chat exit behavior remains stable for users.
3. Context ordering test passes (`## Global Knowledge` before `## Memory`).
4. Empty/unavailable global memory does not crash prompt assembly.

## Phase 4: Hardening and Docs

**Commit message**: `test+docs(memory): harden failure modes and document controls`

**Files**:

- `tests/test_distiller.py`
- `tests/test_sqlite_memory.py`
- `tests/cli/test_chat.py`
- `tests/test_context_builder.py`
- `README.md`
- `src/miminions/memory/MEMORY_EVOLUTION_PLAN.md`

**Scope**:

1. Expand failure-mode coverage:
   - missing/empty session file
   - invalid LLM output schema
   - SQLite unavailable
2. Assert graceful degradation and non-fatal behavior across runtime flows.
3. Document operator controls (confidence threshold, `top_k`, Tier 3 disable option).
4. Document and reinforce source-of-truth contract for local markdown vs global index.

**Done when**:

1. Failure-mode tests are comprehensive and passing.
2. No unhandled exceptions propagate to CLI user flow.
3. Operators can configure memory behavior without reading implementation code.

## Distiller Contract (Reference)

```python
class MemoryDistiller:
   def __init__(self, llm_filter, global_db_path: str | None = None): ...

   def distill_session(
      self,
      workspace,
      root_path,
      session_id: str,
   ) -> DistillationResult: ...
```

`llm_filter` is a callable adapter (or service object) returning structured JSON output. `global_db_path` defaults to `~/.miminions/global_memory.db`.

## Tier 3 Metadata (Reference)

```json
{
  "tier": 3,
  "category": "user_preference|coding_standard|achievement",
  "confidence": 0.93,
  "workspace_id": "...",
  "workspace_name": "...",
  "session_id": "...",
  "source": "distiller",
  "created_at": "ISO-8601"
}
```

## Rollout Notes

1. Start with conservative thresholds to minimize false positives in Tier 3.
2. Prefer under-writing global memory over storing noisy entries.
3. Add lightweight telemetry counters (promoted/dropped counts) for tuning.
4. Keep markdown-first workflow unchanged so existing users are not disrupted.