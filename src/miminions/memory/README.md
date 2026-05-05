# Memory System

How MiMinions stores, evolves, and injects memory across sessions and workspaces.

## Three-Tier Memory

Memory is split into three layers:

| Tier | Storage | Scope | Description |
|---|---|---|---|
| **1** | `memory/HISTORY.md` | Local | One-line chronological log of each session in the workspace. |
| **2** | `memory/MEMORY.md` | Local | Stable, extracted facts and decisions for the workspace. |
| **3** | `global_memory.db` | Global | Reusable cross-workspace insights (stored in SQLite). |

**Markdown is the source of truth.** SQLite is just a read-only index for cross-workspace facts.

## The Memory Lifecycle

The memory system runs in a continuous, automated loop to ensure the agent learns from every interaction without requiring manual context management.

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
Before the agent even speaks, `ContextBuilder` gathers all stored memory. It reads the local `MEMORY.md` (Tier 2) and queries the global SQLite database (Tier 3) for relevant insights. It injects all of this directly into the LLM's system prompt.

### 2. Chat (`Minion`)
The agent reasons and converses with you, fully aware of the facts injected by the context builder. During this time, nothing is written to memory. Instead, the raw conversation is simply appended to a `sessions/*.jsonl` log file.

### 3. Post-Chat (`MemoryDistiller` & `llm_filter`)
When the chat session ends (e.g., you type `exit`), the `MemoryDistiller` spins up in the background. It sends the raw `.jsonl` transcript to the LLM via the `llm_filter`, asking it to extract any *new* project facts, global insights, and a brief session summary. The distiller then disperses these extracted facts to their respective MD/SQLite files, ready for the next session.

## Memory vs. History

| | `MEMORY.md` | `HISTORY.md` |
|---|---|---|
| **Contains** | Stable facts and decisions | Chronological session log |
| **Updated** | Upserted (sections replaced) | Appended (never modified) |
| **Read by agent**| Yes (via ContextBuilder) | No |
