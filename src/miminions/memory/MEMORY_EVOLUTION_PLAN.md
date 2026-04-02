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

## Proposed File and Module Changes

```
docs/
  MEMORY_EVOLUTION_PLAN.md                     # new

src/miminions/memory/
  distiller.py                                # new
  sqlite.py                                   # modified (global DB path helper + metadata helpers)
  __init__.py                                 # modified (export Distiller API)

src/miminions/agent/
  context_builder.py                          # modified (inject ## Global Knowledge before ## Memory)

src/miminions/interface/cli/
  chat.py                                     # modified (run distiller on session exit)

tests/
  test_distiller.py                           # new
  test_context_builder.py                     # modified
  cli/test_chat.py                            # modified
  test_sqlite_memory.py                       # modified or extended for global-tier metadata behavior
```

## Distiller Design (`memory/distiller.py`)

## Public API

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

- `llm_filter` is a callable adapter (or service object) returning structured JSON output.
- `global_db_path` defaults to `~/.miminions/global_memory.db`.

## Distillation Pipeline

1. Load session records from `JsonlSessionStore.iter_messages(session_id)`.
2. Build compact transcript for extraction (strip empty/system noise).
3. Ask LLM for structured output with strict schema:
   - `history_summary`: string (exactly one sentence)
   - `workspace_facts`: list of stable project-specific bullets
   - `global_insights`: list of universal insights with `category`, `confidence`, `evidence`
4. Validate schema and apply deterministic gates:
   - Drop `global_insights` where `confidence < threshold` (recommended `0.85`).
   - Drop statements failing durability/actionability checks.
   - Deduplicate against existing SQLite entries (text normalization + semantic similarity).
5. Promote:
   - Tier 1: `append_history(root_path, history_summary)`
   - Tier 2: `upsert_memory_section(...)` with curated facts
   - Tier 3: `SQLiteMemory.create(text, metadata=...)`
6. Return `DistillationResult` with counts and dropped-item reasons for observability.

## Zero-Fluff Gate (LLM + Rules)

To enforce "zero fluff", use a two-stage filter:

1. LLM extraction prompt that explicitly rejects vague statements.
2. Deterministic post-filter requiring all of:
   - Reusable beyond current workspace
   - Specific and testable wording
   - Durable over time (not tied to one transient task)
   - Confidence score above threshold

If no insight passes, write nothing to Tier 3.

## Metadata for Tier 3 Entries

Recommended metadata payload per global entry:

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

## Context Injection Plan (`ContextBuilder`)

Update `src/miminions/agent/context_builder.py` to:

1. Initialize global memory client at build time (graceful fallback if unavailable).
2. Construct a retrieval query from workspace signals (`workspace_name`, state keys, top rule names, recent prompt headings).
3. Retrieve top global insights (`top_k` small, recommended 5-10).
4. Inject new section before local memory:

```markdown
## Global Knowledge
- [category=user_preference confidence=0.93] User prefers Pydantic for validation.
- [category=coding_standard confidence=0.90] Favor explicit typing for public APIs.

## Memory
...existing MEMORY.md content...
```

5. If DB is empty/unavailable, include explicit placeholder line (`- No global knowledge found.`) or omit section based on config flag.

## Session Exit Integration (`chat.py`)

At `chat start` lifecycle end:

1. Keep existing append behavior for each turn.
2. Wrap REPL loop in `try/finally` so distillation runs on all normal exits (`quit`, `exit`, EOF, Ctrl+C).
3. In `finally`, call `MemoryDistiller.distill_session(...)` with `workspace`, `root`, and `session_id`.
4. Catch distiller exceptions and log a warning without breaking chat command completion.

## Implementation Checklist

1. Create `src/miminions/memory/distiller.py` with:
   - `DistillationResult` model
   - transcript loader
   - LLM extraction call
   - zero-fluff validator
   - tier promotion functions
2. Add global DB path helper in `src/miminions/memory/sqlite.py` targeting `~/.miminions/global_memory.db`.
3. Extend `src/miminions/memory/__init__.py` exports for distiller entry points.
4. Modify `src/miminions/interface/cli/chat.py` to run distillation on session exit in `finally`.
5. Modify `src/miminions/agent/context_builder.py` to inject `## Global Knowledge` before `## Memory`.
6. Add unit tests for distiller behavior:
   - promotes one-line history summary
   - updates workspace memory sections
   - writes only high-confidence insights to Tier 3
   - writes nothing when all candidates are fluff
7. Update context builder tests to assert ordering:
   - `## Global Knowledge` appears before `## Memory`
8. Update CLI chat tests to assert distiller is invoked on `quit`/`exit` and interrupt paths.
9. Add failure-mode tests:
   - missing/empty session file
   - invalid LLM output schema
   - SQLite unavailable (degrade gracefully)
10. Document operator controls in README/docs:
    - confidence threshold
    - top_k retrieval for global injection
    - optional disable flag for Tier 3

## Rollout Notes

- Start with conservative thresholds to minimize false positives in Tier 3.
- Prefer under-writing global memory over storing noisy entries.
- Add lightweight telemetry counters (promoted/dropped counts) for tuning.
- Keep markdown-first workflow unchanged so existing users are not disrupted.