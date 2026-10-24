# Recursive, Bounded Evolution

Status: **Accepted — gated**. Base: `development` @ `f9e466b` (includes PR #125,
`fix/core-memory-management`). Package: `miminions` 0.4.1, Python ≥3.12.

Decisions locked for this spec: (1) deliverable is this design spec first,
(2) the sharing fix targets **context + contracts** first, (3) evolution is
**gated** — a change must satisfy the structure to merge.

## Problem

The repo grew by hand across many branches (16 local, 60+ remote). Knowledge
about what a module does, what it exposes, and how it may change lives in
heads, PR threads, and stale maps. A developer or agent picking up another's
work must reverse-engineer intent. Unbounded growth + ungated sharing is the
defect; the fix is structural, not more documentation volume.

Evidence on `development` today:

- `src/miminions/execution/` is tracked and shipped (`ExecutionService`,
  durable local execution) but absent from `STRUCTURE.md`.
- The CLI actually registers 13 lazy groups in `cli/main.py`
  (`auth agent tool task instance knowledge workspace chat gateway prompt
  config export import`); `STRUCTURE.md` lists 9 and `cli/README.md` lists 10.
- `memory/` gained `budget.py`, `compaction.py`, `dedupe.py` and `context/`
  gained `strategies.py` (with tests) without the map moving.
- `workflow/__init__.py` is empty (no public surface) with no statement of
  whether that is intentional.
- `src/miminions/interface/` exists only as local `__pycache__` residue; it is
  untracked and correctly absent from the map. Gates must ignore it.

## Principles

1. **Recursion (same shape at every scale).** Repo, package, module,
   workspace, and session each carry the same five-block contract (below).
   Learning one level teaches the others.
2. **Bounded.** A level may only be used through its declared public
   surface. Everything else is private and free to change. Cross-level
   writes go through the owner's lifecycle, never around it.
3. **Stable evolution.** A contract change is explicit, versioned, and
   merged together with its contract-doc update and its gate. No silent
   drift: if code and contract disagree, CI fails.
4. **Markdown is the source of truth.** Indexes (SQLite, `STRUCTURE.md`
   tree, MkDocs nav) are derived views. This generalises the existing
   memory rule ("Markdown is the source of truth; SQLite is a read-only
   index") to the whole repo.

## Levels

| Level | Unit | Contract home | Example |
|---|---|---|---|
| L0 | Repo | This doc + `pyproject.toml` + CI | `miminions` 0.4.1, entry `miminions = miminions.cli.main:main` |
| L1 | Package | `STRUCTURE.md` import surface | `from miminions.agent import create_minion` |
| L2 | Module | `src/miminions/<module>/README.md` | `memory`, `context`, `execution` |
| L3 | Workspace | `prompt/ memory/ skills/ sessions/ data/` (`WorkspaceLayout`) | Bootstrap files `AGENTS.md USER.md TOOLS.md IDENTITY.md` |
| L4 | Session | `sessions/*.jsonl` → distiller | One chat, distilled on exit |

## The five-block contract

Every level, and every L2 module, states exactly these blocks. A missing
block means the level is not yet contracted — the gate reports it.

1. **Purpose** — one paragraph: what this owns, what it never does.
2. **Public surface** — the only stable API (usually the package
   `__init__.py` `__all__`, a CLI group, or an on-disk layout). Callers
   import from here; deep imports are unsupported.
3. **State** — what it owns on disk/in memory, and which artefact is the
   source of truth vs a derived index.
4. **Lifecycle** — how it is created, how it changes, and how change
   promotes one level up (e.g. session → workspace → global).
5. **Gate** — the automated check(s) that prove 1–4 still hold, runnable
   locally with one command.

Header per contract: **Owner** (team/role), **Version** (bump on any
breaking surface/state change, with a migration note — following the
existing `WORKSPACE_SCHEMA_VERSION` pattern in `core/workspace.py`).

## Sharing loop (context + contracts)

The loop already exists for memory; this spec makes it the repo-wide
handoff protocol:

```text
L4 session (sessions/*.jsonl, JsonlSessionStore)
  → MemoryDistiller + llm_filter (extract facts, dedupe, budget/compaction)
  → L3 workspace memory/MEMORY.md (Tier 2, upserted) + memory/HISTORY.md
    (Tier 1, append-only)
  → Tier 3 global_memory.db (cross-workspace, deduped index)
  → ContextBuilder (prompt/ + MEMORY + global + skills) → next L4 session
```

Rule: a PR leaves its decision in the owning module's contract/doc, not
only in the PR thread. The next developer/agent enters through the
contract, not through archaeology.

## Contract registry (L2 modules, `development` @ `f9e466b`)

Public surface is the module `__init__.py` `__all__` unless noted. Full
contracts live in each module `README.md`; this table is the index.

| Module | Public surface (stable) | State owner | Lifecycle / promotion |
|---|---|---|---|
| `agent` | `Minion`, `create_minion`, `AgentConfig`, `AgentState` (lazy) | In-memory agent; attached `BaseMemory` | `set_context()` rebuilds prompt via `ContextBuilder` each run |
| `cli` | `cli` (13 lazy groups + standalone `init`, see `cli/main.py`) | `~/.miminions/` (`MIMINIONS_HOME`) | Bootstrap on first real subcommand; help stays lazy/cheap |
| `context` | `ContextBuilder` | None (pure assembly) | Reads L3 prompt/memory/skills + Tier 3 → system prompt string |
| `core` | Gateway symbols only; workspace/auth via submodules | Workspace JSON (`WorkspaceManager`, schema v1) | `ensure_default_setup()` idempotent first run |
| `data` | `LocalDataManager` | Content-addressed files + master index + txn log | SHA-256 dedupe; append-only audit log |
| `execution` | `ExecutionService`, `ExecutionRequest/Task/Event/Handle` | Durable store under config home | Persistent worker (`-m miminions.execution.worker`); terminal = completed/failed/cancelled |
| `memory` | `MemoryDistiller`, `create_llm_filter`, `compact_memory`, budgets, md_store helpers | Tier 1/2 Markdown (truth) + Tier 3 SQLite (index) | Post-chat distill → upsert → dedupe/compaction under budget |
| `session` | `JsonlSessionStore`, `create_session_id` | `sessions/*.jsonl` transcripts | Append during chat; history trimmed at turn boundaries |
| `task` | `TaskRuntime`, `Task`, `AgentTask`, `TaskStatus`, `TaskPriority` | In-memory runtime (`DEFAULT_RUNTIME`) | Async add/run/update; distinct from durable `execution` |
| `tools` | `GenericTool`, `create_tool`, `tool`, `ToolSchema` (dataclass) | None | Function → schema → agent/MCP; pydantic `ToolSchema` in `schemas.py` is internal — do not confuse the two |
| *(removed)* `user` | — | — | Removed 2026-10-23 (OQ-11): zero callers; returns via ADR if account features are scoped |
| `utils` | `generate_*`, `load_json/save_json`, `append_transcript` | None | Pure helpers; no domain state |
| *(removed)* `workflow` | — | — | Removed 2026-10-23 (OQ-10): trace types moved to `execution.trace` (schema v2 unchanged); controller had no production callers |
| `workspace_fs` | `WorkspaceLayout`, `BOOTSTRAP_PROMPT_FILES`, `init_workspace`, readers | On-disk L3 layout | `init_workspace()` scaffolds; readers omit missing files |

Invariants that must never regress: `core/__init__` re-exports gateway
only; the two `ToolSchema` types stay distinct and documented; `task`
(in-memory) and `execution` (durable) never merge silently; Markdown
outranks SQLite on conflict.

## Gated evolution

Branch per `CONTRIBUTING.md` (`feature/*`/`fix/*`/`enhance/*` off
`development`, `hotfix/*` off `main`). A change is mergeable only when:

1. Code, contract (Purpose/Surface/State/Lifecycle), and gate move
   together in the same PR. Surface/state breaks bump the contract
   version and add a migration note.
2. `scripts/check_structure.py` passes (map ↔ tree ↔ nav ↔ README ↔
   CLI groups agree; `__pycache__`/untracked residue ignored).
3. Existing CI passes: `pytest`, `ruff check`, `mkdocs build --strict`,
   `python -m build`, plus module contract tests.
4. The PR template's contract checklist is answered (touched? version?
   migration?). Review verifies the contract, CI verifies the claim.

Rollback: contracts are docs + a check script; reverting the PR reverts
both. No data migration is implied by this spec.

## Internal-docs boundary

Organisation-internal documentation (roadmap, backlog, ADRs, working
provenance, test practice notes) lives in the private
`MiMinions-ai/docs-internal` repo — never on this site and never in this
repo. The gate fails if `memory/` or `docs/test-quality-control.md`
reappears here. Public docs answer "what should a user do"; internal
docs answer "why did we decide it, what is broken, what is next".

## Compatibility

Stable across this change: Python ≥3.12, `pydantic-ai>=1.0.0,<2.0.0`,
console entry `miminions`, `~/.miminions/` home (`MIMINIONS_HOME`),
workspace on-disk layout, and every Public surface row above. Only docs,
`STRUCTURE.md`, the check script, CI wiring, and missing READMEs are
added; no runtime API moves.

## Non-goals

No new runtime feature, no module rename, no branch cleanup, no wiki or
external docs host, no hand-maintained duplicate of this registry (the
gate checks the table's module set against the tree).

## Adoption checklist

- [x] This spec linked from MkDocs nav and `STRUCTURE.md`.
- [x] Every L2 module has a `README.md` carrying the five blocks.
- [x] `STRUCTURE.md` matches the tracked tree (incl. `execution`,
      13 CLI groups, new memory/context files).
- [x] `scripts/check_structure.py` green locally and in CI; deliberate
      drift (rename without map update) makes it fail.
- [x] Cold-start test: a fresh agent, repo only, stated every sampled
      module's surface, state, and invariants (and caught the standalone
      `init` command the gate had missed; gate now covers it and verifies
      every `__all__` export is documented). That is the sharing criterion.
