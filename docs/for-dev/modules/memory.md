# Memory System

MiMinions uses a three-tier memory architecture that automatically evolves across sessions without manual intervention. Two markdown tiers live inside each workspace; a global SQLite vector store carries reusable insights between workspaces.

## Three-Tier Memory

| Tier | Storage | Scope | Description |
|------|---------|-------|-------------|
| **1** | `memory/HISTORY.md` | Workspace-local | One-line chronological log of each session |
| **2** | `memory/MEMORY.md` | Workspace-local | Stable extracted facts and decisions |
| **3** | `~/.miminions/global_memory.db` | Global | Reusable cross-workspace insights (SQLite vector) |

The markdown files (Tiers 1 and 2) live under `<workspace_root>/memory/` and are the human-readable source of truth. The global SQLite database (Tier 3) is a vector index for cross-workspace recall.

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

Before the agent responds, [`ContextBuilder`](context.md) reads `MEMORY.md` (Tier 2) and queries the global SQLite database (Tier 3) for relevant insights, then injects both into the system prompt. The Tier-3 "Global Knowledge" section only appears when `global_top_k > 0` and matching insights exist.

### During Chat: `Minion`

The agent reasons with full memory context already injected. Raw conversation turns are appended to a `sessions/*.jsonl` log — nothing is written to memory during the session.

### Post-Chat: `MemoryDistiller` + `llm_filter`

When the session ends (e.g., typing `exit`), `MemoryDistiller` sends the `.jsonl` transcript to the LLM via `llm_filter`, which extracts:

- A brief session summary → appended to `HISTORY.md` (Tier 1)
- New workspace facts → upserted into the `Project Facts` section of `MEMORY.md` (Tier 2)
- Global insights → inserted (deduped) into `global_memory.db` (Tier 3)

```python
from miminions.memory import MemoryDistiller, create_llm_filter
from miminions.agent.provider import ModelFactory

# Build an extraction filter backed by any pydantic_ai model
llm_filter = create_llm_filter(ModelFactory.create("openrouter"))

distiller = MemoryDistiller(llm_filter)  # global_db_path defaults to ~/.miminions/global_memory.db
result = distiller.distill_session(workspace, root_path, session_id="20260101T120000Z_ab12cd34")

print(result.history_summary)     # Tier-1 summary text
print(result.workspace_facts)     # Tier-2 facts
print(result.global_insights)     # Tier-3 insights actually stored
print(result.promoted_counts)     # {"tier1": 1, "tier2": 3, "tier3": 2}
print(result.dropped_reasons)     # human-readable notes on anything skipped
```

!!! note "Failures are recorded, not raised"
    `distill_session` is resilient: an empty transcript, a failing `llm_filter`, or an unavailable Tier-3 store are all captured in `result.dropped_reasons` (e.g. `"empty_session: ..."`, `"llm_filter_error: ..."`, `"tier3_unavailable: ..."`) rather than throwing. `create_llm_filter` likewise returns the raw model output (first 500 chars) as the summary if the model does not return valid JSON.

## Storage Comparison

| | `HISTORY.md` (Tier 1) | `MEMORY.md` (Tier 2) | `global_memory.db` (Tier 3) |
|-|-----------------------|----------------------|-----------------------------|
| **Contains** | Chronological session log | Stable facts and decisions | Cross-workspace insights |
| **Updated by** | MemoryDistiller (append) | MemoryDistiller (upsert) | MemoryDistiller (deduped insert) |
| **Read by agent** | No | Yes | Yes |

## Markdown Store Helpers

The two markdown tiers are powered by small, dependency-free helpers in `md_store`. They operate on a workspace root and create `memory/MEMORY.md` and `memory/HISTORY.md` from default templates on first use.

```python
from miminions.memory import (
    append_history,
    read_memory,
    write_memory,
    upsert_memory_section,
)

append_history(root_path, "Set up CI and pinned dependencies")      # → Tier 1
upsert_memory_section(root_path, "Project Facts", ["Uses pytest", "Python 3.12"])  # → Tier 2
content = read_memory(root_path)   # full text of MEMORY.md
write_memory(root_path, content)   # replace MEMORY.md wholesale
```

| Function | Signature | Purpose |
|----------|-----------|---------|
| `append_history` | `append_history(root_path, line) -> Path` | Append one bullet to `HISTORY.md`. |
| `read_memory` | `read_memory(root_path) -> str` | Read the full text of `MEMORY.md`. |
| `write_memory` | `write_memory(root_path, content) -> Path` | Replace the entire contents of `MEMORY.md`. |
| `upsert_memory_section` | `upsert_memory_section(root_path, heading, bullets) -> Path` | Insert or replace a `## {heading}` section with bullet items. |

!!! tip "These are the building blocks"
    `MemoryDistiller` calls `append_history` and `upsert_memory_section` for you. Reach for these helpers directly when you want to script the markdown tiers without an LLM in the loop. See [Workspaces](workspaces.md) for the on-disk `memory/` layout.

## SQLite Vector Memory

For direct vector search, `SQLiteMemory` implements the abstract `BaseMemory` CRUD interface plus several search strategies, backed by [`sqlite-vec`](https://github.com/asg017/sqlite-vec). Embeddings are generated locally with [`fastembed`](https://github.com/qdrant/fastembed) (ONNX runtime — no PyTorch or CUDA required), so you store and query plain text.

!!! warning "Import path and extra"
    `SQLiteMemory` is **not** re-exported from `miminions.memory`. Import it from the submodule, and install the `sqlite` extra:

    ```bash
    pip install miminions[sqlite]
    ```

    ```python
    from miminions.memory.sqlite import SQLiteMemory   # ✅
    # from miminions.memory import SQLiteMemory         # ✗ not exported
    ```

### Quick Start

```python
from miminions.memory.sqlite import SQLiteMemory

# Persistent on-disk store (creates parent dirs as needed)
memory = SQLiteMemory("memory.db")

entry_id = memory.create("Python is a programming language", metadata={"tag": "tech"})

results = memory.read("languages for coding", top_k=5)
for r in results:
    print(r["id"], r["distance"], r["text"], r["meta"])

memory.update(entry_id, "Python is a high-level programming language")
memory.delete(entry_id)
memory.close()
```

`SQLiteMemory` is also a **context manager** — the connection closes automatically on exit:

```python
with SQLiteMemory("memory.db") as memory:
    memory.create("Python is a programming language")
    results = memory.read("languages for coding", top_k=5)
```

The constructor `SQLiteMemory(db_path=None, model_name="all-MiniLM-L6-v2", dim=384)` resolves storage by `db_path`:

=== "Persistent (path)"

    ```python
    SQLiteMemory("knowledge.db")   # stored at the given path
    ```

=== "Persistent (default)"

    ```python
    SQLiteMemory()                 # default location inside the package
    ```

=== "Ephemeral"

    ```python
    SQLiteMemory(":memory:")       # in-process, lost when the process ends
    ```

!!! note "`model_name` and `dim` must agree"
    The default model is `all-MiniLM-L6-v2` (aliased to `sentence-transformers/all-MiniLM-L6-v2`), which produces 384-dimensional vectors. If you pass a different `model_name`, set `dim` to match its output or vector inserts will fail. The model downloads on first use.

### Result shape

All search methods return a list of dicts. Every dict carries `id`, `text`, and **`meta`** (the parsed metadata — note the key is `meta`, **not** `metadata`). Some methods add extra keys:

| Method | Extra keys |
|--------|------------|
| `read` (vector KNN) | `distance` |
| `date_time_search` | `created_at` |
| `hybrid_search` | `source` (`"vector"` or `"keyword"`) |

### CRUD and search methods

```python
# Exact and text matches
memory.get_by_id(entry_id)
memory.get_by_keyword("python", top_k=5)
memory.full_text_search("high level language", top_k=5)   # all words must appear
memory.regex_search(r"\bpython\b", top_k=5)               # IGNORECASE re.search

# Structured and time filters
memory.metadata_search("tag", "tech", top_k=5)            # json_extract on metadata
memory.date_time_search(start="2026-01-01", end="2026-06-21", top_k=5)

# Combined vector + keyword
memory.hybrid_search("coding languages", top_k=5)

# Bulk
memory.list_all()
memory.clear()
memory.close()
```

| Method | Description |
|--------|-------------|
| `create(text, metadata=None) -> str` | Embed and store text; returns a new uuid id. |
| `read(query, top_k=5) -> list[dict]` | Vector KNN search; results include `distance`. |
| `update(id, new_text) -> bool` | Re-embed and replace text; `False` if id missing. |
| `delete(id) -> bool` | Remove an entry; `True` if a row was deleted. |
| `get_by_id(id) -> dict \| None` | Fetch a single entry by id. |
| `get_by_keyword(keyword, top_k=5)` | Case-insensitive `LIKE %keyword%` match. |
| `full_text_search(query, top_k=5)` | Require every word of the query to appear. |
| `metadata_search(key, value, top_k=5)` | Filter by a metadata key/value pair. |
| `regex_search(pattern, top_k=5)` | Match text against a regex (`IGNORECASE`). |
| `hybrid_search(query, top_k=5)` | Merge vector + keyword results, deduped, tagged with `source`. |
| `date_time_search(start=None, end=None, top_k=5)` | Filter by `created_at` range; adds `created_at`. |
| `list_all() -> list[dict]` | Return every entry (no limit). |
| `clear() -> None` | Delete all entries. |
| `close()` | Close the underlying SQLite connection. |
| `__enter__` / `__exit__` | Context-manager support; `with SQLiteMemory(...) as mem:` closes the connection on exit. |

!!! note "Extension support"
    `SQLiteMemory` needs SQLite extension loading. The `sqlite` extra installs `pysqlite3` for this; if your Python's `sqlite3` lacks extension support, the constructor raises `RuntimeError("SQLite extension loading not supported. Install pysqlite3: pip install pysqlite3")`.

### Global memory path

The canonical cross-workspace database lives at `~/.miminions/global_memory.db` (or under `$MIMINIONS_HOME` if that environment variable is set). Resolve it programmatically with:

```python
from miminions.core.paths import get_global_memory_db_path

path = get_global_memory_db_path()   # creates the config dir if needed
```

The function's canonical home is `miminions.core.paths`; it is still re-exported from `miminions.memory.sqlite` for backwards compatibility.

## Attaching memory to an agent

A `SQLiteMemory` instance can be attached to a [`Minion`](agent.md) so the agent gets memory CRUD and document-ingestion tools automatically, plus `store_knowledge` / `recall_knowledge` helpers:

```python
from miminions.agent import create_minion
from miminions.memory.sqlite import SQLiteMemory

agent = create_minion("researcher", memory=SQLiteMemory(":memory:"))
agent.store_knowledge("The release ships on Friday", metadata={"topic": "release"})
hits = agent.recall_knowledge("when do we ship?", top_k=3)
```

When memory is attached, seven tools auto-register: `memory_store`, `memory_recall`, `memory_update`, `memory_delete`, `memory_get`, `memory_list`, and `ingest_document`. See [Agent](agent.md) for the full integration.

## See also

- [Context Builder](context.md) — how memory tiers are composed into the system prompt.
- [Workspaces](workspaces.md) — the on-disk `memory/` layout and workspace model.
- [Agent](agent.md) — attaching memory and the auto-registered memory tools.
