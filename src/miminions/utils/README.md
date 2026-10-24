# Utils (Pure Helpers)

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).

## Purpose

Small, dependency-light helpers shared across modules: text chunking for
ingestion, random name/description generation, JSON file IO, and
transcript appending. Owns no domain state and makes no policy decisions —
if a helper grows rules, it moves to the owning module.

## Public surface

```python
from miminions.utils import (
    generate_random_name, generate_random_description,
    load_json, save_json, append_transcript,
)
# TextChunker lives in miminions.utils.chunker (chunk_size=800, overlap=150).
```

## State

None. Functions are pure or thin filesystem adapters (`json_io`,
`session.append_transcript`); callers own the paths and formats.

## Lifecycle

Stateless. No bootstrap, no promotion. Changes must stay backward
compatible for all callers (search before changing a signature).

## Gate

Importer test suites plus `scripts/check_structure.py`. Contract version: 1.
