# Memory System

MiMinions uses a three-tier memory architecture that automatically evolves across sessions without manual intervention.

## Three-Tier Memory

| Tier | Storage | Scope | Description |
|------|---------|-------|-------------|
| **1** | `memory/HISTORY.md` | Workspace-local | One-line chronological log of each session |
| **2** | `memory/MEMORY.md` | Workspace-local | Stable extracted facts and decisions |
| **3** | `global_memory.db` | Global | Reusable cross-workspace insights (SQLite) |

Markdown files are the source of truth. SQLite is a read-only index for cross-workspace queries.

## The Memory Lifecycle

```
  [ContextBuilder]                            [Minion Agent]
  Reads Tier 2 & 3        System Prompt       Reasons & chats
  at startup     ────────────────────────►    with the user
                                                    │
                                                    │ (Chat ends)
  [Next Session]                                    ▼
  ContextBuilder         MD & SQLite        [MemoryDistiller]
  reads the newly  ◄──────────────────────   Uses llm_filter
  updated files          Upserts facts        to parse JSONL
```

### Pre-Chat: `ContextBuilder`

Before the agent responds, `ContextBuilder` reads `MEMORY.md` (Tier 2) and queries the global SQLite database (Tier 3) for relevant insights, then injects both into the system prompt.

### During Chat: `Minion`

The agent reasons with full memory context already injected. Raw conversation turns are appended to a `sessions/*.jsonl` log — nothing is written to memory during the session.

### Post-Chat: `MemoryDistiller` + `llm_filter`

When the session ends (e.g., typing `exit`), `MemoryDistiller` sends the `.jsonl` transcript to the LLM via `llm_filter`, which extracts:

- New workspace facts → upserted into `MEMORY.md`
- Global insights → inserted (deduped) into `global_memory.db`
- A brief session summary → appended to `HISTORY.md`

## Storage Comparison

| | `MEMORY.md` (Tier 2) | `HISTORY.md` (Tier 1) | `global_memory.db` (Tier 3) |
|-|----------------------|-----------------------|-----------------------------|
| **Contains** | Stable facts and decisions | Chronological session log | Cross-workspace insights |
| **Updated by** | MemoryDistiller (upsert) | MemoryDistiller (append) | MemoryDistiller (deduped insert) |
| **Read by agent** | Yes | No | Yes |

## SQLite Vector Memory

For direct vector search, `SQLiteMemory` provides CRUD, keyword, and full-text search backed by `sqlite-vec`.

Embeddings are generated locally with `fastembed` (the `all-MiniLM-L6-v2` model, 384-dim) — no PyTorch/CUDA required — so you store and query plain text:

```python
from miminions.memory.sqlite import SQLiteMemory

memory = SQLiteMemory("memory.db")
memory.create("Python is a programming language", metadata={"tag": "tech"})

results = memory.read("languages for coding", top_k=5)
```

Requires the `sqlite` extra: `pip install miminions[sqlite]`
