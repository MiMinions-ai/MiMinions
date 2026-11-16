# Utils (Shared Helpers)

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).

## Purpose

Small, dependency-light helpers shared across modules: text chunking for
ingestion, random name/description generation, JSON file IO, and
an example transcript helper. Owns no separate domain store —
if a helper grows rules, it moves to the owning module.

`append_transcript` is re-exported from
[interface.session](../interface/session.py) and appends a fixed example
conversation. Use `JsonlSessionStore` there for real conversation records.
JSON helpers perform filesystem IO; "utility" does not mean "pure function".

## Public surface

```python
from miminions.utils import (
    generate_random_name, generate_random_description,
    load_json, save_json, append_transcript,
)
# Exact public surface (`__init__.__all__`): generate_random_name,
# generate_random_description, load_json, save_json, append_transcript.
# The gate verifies every exported name appears in this README.
# TextChunker lives in miminions.utils.chunker (chunk_size=800, overlap=150).
```

## State

No independent persistent store. Callers supply paths to JSON helpers;
the transcript helper writes through the session store.

## Lifecycle

Stateless. No bootstrap, no promotion. Changes must stay backward
compatible for all callers (search before changing a signature).

## Gate

Importer test suites plus `scripts/check_structure.py`. Contract version: 1.
