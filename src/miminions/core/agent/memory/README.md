# Agent Memory Contracts and Shared API

`miminions.core.agent.memory` defines backend contracts and result types, and
provides a shared import surface for the wider memory system. It does not contain
all memory implementations.

> Full reference: [Memory documentation](https://miminions.ai/modules/memory/),
> including the `SQLiteMemory` vector store API.

## Implementation ownership

| Responsibility | Implementation |
|----------------|----------------|
| Backend interface and memory result types | [base_memory.py](base_memory.py), [types.py](types.py). Import these from their concrete modules. |
| Distillation, compaction, budgets and LLM extraction | [core.context](../../context/README.md); helpers are re-exported here. |
| Workspace Markdown reads/writes | [system.file.md_store](../../../system/file/md_store.py); helpers are re-exported here. |
| Vector-memory database | [system.db.sqlite](../../../system/db/sqlite.py), using the `sqlite` extra. |
| Raw conversation transcripts | [interface.session](../../../interface/session.py), not this package. |

The separate `knowledge` CLI manages versioned `knowledge.json` records. Its
name does not make it the owner of these memory backends or the agent's
`store_knowledge()` / `recall_knowledge()` helpers.

## Three-Tier Memory

Memory is split into three layers:

| Tier | Storage | Scope | Description |
|---|---|---|---|
| **1** | `memory/HISTORY.md` | Local | One-line chronological log of each session in the workspace. |
| **2** | `memory/MEMORY.md` | Local | Stable, extracted facts and decisions for the workspace. |
| **3** | `global_memory.db` | Global | Reusable cross-workspace insights (stored in SQLite). |

Markdown holds workspace summaries and stable facts. Global SQLite holds
cross-workspace insights and receives writes from distillation and compaction;
it is not read-only, nor necessarily a complete mirror of Markdown. The
architecture's Markdown-first policy does not provide automatic conflict
reconciliation between arbitrary stores.

## The Memory Lifecycle

The CLI can queue post-chat distillation; SDK callers may invoke it explicitly.
Extraction depends on the configured filter/model and can produce no new facts.

```text
  [ContextBuilder]                              [Minion Agent]
  Reads Tier 2 & 3           System Prompt      Reasons & chats 
  memory at startup  ────────────────────────►  with the user
                                                      │
                                                      │ (Chat ends)
  [Next Session]                                      ▼
  ContextBuilder             MD & SQLite      [MemoryDistiller]
  reads the newly    ◄────────────────────────  Uses llm_filter
  updated files             Upserts facts       to parse JSONL
```

### 1. Pre-Chat (`ContextBuilder`)
`ContextBuilder` reads local `MEMORY.md` (Tier 2) and optionally queries a limited
number of recent global SQLite insights (Tier 3). Section budgets/strategies can
limit what reaches the prompt; it does not inject every stored memory.

### 2. Chat (`Minion`)
The prompt/chat execution handler appends transcript records and saves native
model-message checkpoints. An attached memory backend also exposes CRUD and
ingestion tools, so an agent may write memory during a turn.

### 3. Post-Chat (`MemoryDistiller` & `llm_filter`)
When a CLI chat with submitted turns ends (for example via `/exit`), it queues a
distillation task. `MemoryDistiller` reads and shortens the transcript, invokes
the configured filter, then appends history, upserts workspace facts and inserts
global insights. It compacts `MEMORY.md` when over budget; the default distillation
path does not trim history.

## Memory vs. History

| | `MEMORY.md` (Tier 2) | `HISTORY.md` (Tier 1) | `global_memory.db` (Tier 3) |
|---|---|---|---|
| **Contains** | Stable facts and decisions | Chronological session log | Reusable cross-workspace insights |
| **Scope** | Workspace-local | Workspace-local | Global |
| **Updated** | Upserted or compacted | Appended; explicit history-budget enforcement can trim oldest lines | Written through the SQLite backend |
| **Read by agent** | Yes (via ContextBuilder) | No | Yes (via ContextBuilder) |

## Contract

> [Recursive, Bounded Evolution](../../../../../docs/architecture/recursive-evolution.md) — Contract v1.
> **Public surface:** exactly `__init__.__all__`: `append_history`, `delete_memory_section`, `search_memory_sections`, `read_memory`, `upsert_memory_section`, `write_memory`, `DistillationResult`, `MemoryDistiller`, `create_llm_filter`, `CompactionOutcome`, `MemoryBudgets`, `TierStatus`, `check_pressure`, `compact_memory` (`create_llm_compactor` is imported but not exported); `SQLiteMemory` via `miminions.system.db.sqlite` (needs `[sqlite]`).
> **State:** backend contracts/types live here; the owning context and storage modules manage Tier 1/2 Markdown and Tier 3 SQLite. The stores are distinct, not automatically interchangeable.
> **Lifecycle:** optional memory tools during a turn; post-chat distillation and budget-driven compaction; later prompt assembly reads the resulting memory.
> **Gate:** `tests/integration/memory/` + `tests/integration/context/` + `scripts/check_structure.py`.
