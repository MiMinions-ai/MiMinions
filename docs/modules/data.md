# Data Management

The `miminions.data` module provides **`LocalDataManager`** — a pure-Python, content-addressable store for files and raw content. It hashes every blob with SHA-256, deduplicates identical content automatically, tracks rich metadata in a JSON master index, and records every operation in an append-only transaction log for a full audit trail.

!!! note "Import from the subpackage"
    `LocalDataManager` is exported from `miminions.data` (and also from `miminions.data.local`). The top-level `import miminions` does not re-export it.

    ```python
    from miminions.data import LocalDataManager
    ```

This is a **library API**, not a CLI — there are no `miminions data ...` commands. It has no third-party dependencies.

## How it works

A `LocalDataManager` is composed of four cooperating parts, all rooted under a single base directory (defaults to `~/.miminions`):

<div class="grid cards" markdown>

- :material-content-save: **Content-addressable storage**

    Each blob is named by the SHA-256 hash of its content and written under a two-level directory fan-out (`data/ab/cd/abcd…`). Storing the same bytes twice is a no-op — **identical content is deduplicated automatically**.

- :material-table: **Master index**

    A JSON index of `FileMetadata` records (id, original name, hash, type, size, tags, description, author, timestamps, access count). This is what you search and list.

- :material-history: **Transaction log**

    An append-only JSONLines log of every read, write, update, and delete — your audit trail. Query it per-file or as a recent-activity feed.

- :material-file-cog: **File handlers**

    A `FileHandlerRegistry` dispatches by file type to extract per-type metadata: line/word/char counts for **text**, headers and code/table/link flags for **markdown**, delimiter/header/column info for **csv**. Unrecognized files are stored as `binary`.

</div>

## Quick Start

```python
from miminions.data import LocalDataManager

# Defaults: base_dir=~/.miminions, author=current OS user
dm = LocalDataManager(base_dir="./.data", author="asher")

# Add a file from disk — returns a file id
file_id = dm.add_file(
    "README.md",
    description="Project readme",
    tags=["docs"],
)

# Or add content directly, no file on disk required
note_id = dm.add_content(
    "Release ships on Friday",
    name="release-note.txt",
    file_type="text",
    tags=["release"],
)

# Read it back as text (None if the id is unknown)
text = dm.get_content(note_id)
print(text)  # "Release ships on Friday"

# Inspect metadata
meta = dm.get_file(file_id)
print(meta.original_name, meta.file_type, meta.size_bytes, meta.tags)
```

!!! tip "Storing bytes and writing files out"
    `add_content` accepts `str` **or** `bytes`. Retrieve binary blobs with `get_binary_content(file_id)`, or copy a stored blob back to disk with `extract_file(file_id, destination)`.

## Searching and listing

The master index supports filtering by name substring, file type, tags (all must match), and author. Everything returns `FileMetadata` objects.

```python
# All files, newest first
for meta in dm.list_files():
    print(meta.id, meta.original_name)

# Filtered search — any combination of criteria
hits = dm.search_files(name_pattern="readme", file_type="markdown", tags=["docs"])

# Facets across the whole index
dm.get_tags()        # -> sorted unique tags
dm.get_file_types()  # -> sorted unique file types
dm.get_authors()     # -> sorted unique authors
```

## Audit trail

Every operation is logged. Pull a file's full history or a recent-activity feed of `TransactionRecord` objects (newest first).

```python
# Everything that ever happened to one file
history = dm.get_file_history(file_id)

# The last N operations across all files (default 100)
recent = dm.get_recent_activity(limit=20)

for rec in recent:
    print(rec.timestamp, rec.transaction_type.value, rec.file_name, rec.author)
```

## Updating and deleting

```python
# Patch index metadata (description, tags, ...). Returns False if id unknown.
dm.update_metadata(file_id, {"description": "Updated readme", "tags": ["docs", "v2"]})

# Remove from the index; remove_storage=True also unlinks the stored blob
dm.delete_file(file_id, remove_storage=True)
```

!!! warning "Deletion does not reference-count deduplicated blobs"
    Because storage is content-addressable, two index entries with identical content share **one** physical blob. `delete_file(..., remove_storage=True)` unlinks that blob unconditionally — so deleting one entry can remove content still referenced by another. Pass `remove_storage=False` to drop the index entry while leaving the blob in place.

!!! warning "Single-process use only"
    `LocalDataManager` keeps the master index in memory and rewrites it on every change. It is **not** designed for concurrent or multi-process access — running two managers against the same `base_dir` at once can lose writes. Use it from a single process.

## Stats, backup, and restore

```python
# Aggregate stats: index, storage, and transaction-log summaries
stats = dm.get_stats()
print(stats["index"]["total_files"], stats["storage"]["total_size_mb"])

# Snapshot the entire base_dir; restore replaces the current store
dm.backup_system("./backups")          # -> True on success
dm.restore_from_backup("./backups")    # -> True on success
```

!!! note
    `backup_system` and `restore_from_backup` return `False` (and print a message) on failure rather than raising. `add_file` raises `FileNotFoundError` for a missing source path and `ValueError` if a blob cannot be stored.

## API Reference

### `LocalDataManager`

```python
LocalDataManager(base_dir: str | Path | None = None, author: str | None = None)
```

`base_dir` defaults to `~/.miminions`; `author` defaults to the current OS user and is recorded on every operation.

| Method | Description |
|--------|-------------|
| `add_file(file_path, name=None, description="", tags=None, author=None) -> str` | Store a file from disk; returns its file id. Raises `FileNotFoundError` / `ValueError`. |
| `add_content(content, name, file_type="text", description="", tags=None, author=None, encoding="utf-8") -> str` | Store `str` or `bytes` directly; returns the file id. |
| `get_file(file_id, author=None) -> FileMetadata \| None` | Fetch metadata (bumps the access count); `None` if not found. |
| `get_content(file_id, author=None, encoding="utf-8") -> str \| None` | Retrieve stored content as text. |
| `get_binary_content(file_id, author=None) -> bytes \| None` | Retrieve stored content as bytes. |
| `extract_file(file_id, destination, author=None) -> bool` | Copy a stored blob back out to `destination`. |
| `update_metadata(file_id, updates, author=None) -> bool` | Patch index fields; `False` if the id is unknown. |
| `delete_file(file_id, author=None, remove_storage=True) -> bool` | Remove from the index (and optionally the blob). |
| `search_files(name_pattern=None, file_type=None, tags=None, author=None) -> list[FileMetadata]` | Filter the index (newest first). |
| `list_files() -> list[FileMetadata]` | All files, newest first. |
| `get_tags() -> list[str]` | Sorted unique tags. |
| `get_file_types() -> list[str]` | Sorted unique file types. |
| `get_authors() -> list[str]` | Sorted unique authors. |
| `get_file_history(file_id) -> list[TransactionRecord]` | Full transaction history for one file. |
| `get_recent_activity(limit=100) -> list[TransactionRecord]` | Recent operations across all files. |
| `get_stats() -> dict` | Combined index, storage, and log statistics. |
| `backup_system(backup_path) -> bool` | Snapshot the entire store. |
| `restore_from_backup(backup_path) -> bool` | Replace the store from a snapshot. |

### `FileMetadata`

A dataclass describing one stored item, returned by `get_file`, `list_files`, and `search_files`. Import it (and the other building blocks) from `miminions.data.local`:

```python
from miminions.data.local import FileMetadata, TransactionRecord, TransactionType
```

| Field | Type | Notes |
|-------|------|-------|
| `id` | `str` | Generated UUID. |
| `original_name` | `str` | Display name (or source filename). |
| `original_path` | `str` | Source path (empty for `add_content`). |
| `file_hash` | `str` | SHA-256 of the content. |
| `file_type` | `str` | `text` / `markdown` / `csv` / `binary` / custom. |
| `size_bytes` | `int` | Content size. |
| `tags` | `list[str]` | User tags plus handler-derived defaults. |
| `description` | `str` | Free-text description. |
| `author` | `str` | Who added it. |
| `created_at` / `updated_at` | `str` | ISO-8601 UTC timestamps. |
| `access_count` | `int` | Incremented on each read. |
| `last_accessed` | `str \| None` | ISO-8601 UTC timestamp of last read. |

### `TransactionRecord`

Each audit-log entry. `transaction_type` is a `TransactionType` enum: `READ`, `WRITE`, `UPDATE`, `DELETE`, `CREATE_INDEX`, `ROTATE_LOG`. Key fields include `id`, `timestamp`, `file_id`, `file_hash`, `file_name`, `author`, `details`, `success`, and `error_message`.

## See also

<div class="grid cards" markdown>

- :material-database: **[Memory](memory.md)** — vector and markdown memory for an agent
- :material-robot: **[Agent](agent.md)** — the `Minion` agent and its tools
- :material-graph: **[Workspaces](workspaces.md)** — the on-disk workspace layout under `~/.miminions`

</div>
