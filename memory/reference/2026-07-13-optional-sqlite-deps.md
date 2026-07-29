# Provenance Record: Optional sqlite dependency imports

## Task

Fix test-time import failures when optional packages (`sqlite_vec`, `fastembed`) are not installed.

## Sources

- Existing repository code only (no external web sources used).
- Direct references:
  - `src/miminions/memory/sqlite.py`
  - `tests/integration/test_sqlite_memory.py`
  - `tests/integration/test_document_ingestion.py`

## Decisions

- Changed `sqlite_vec` and `fastembed` imports to optional in module scope.
- Deferred missing dependency failures to `SQLiteMemory.__init__` with clear RuntimeError messages.
- Added test-level conditional skip for suites that explicitly require sqlite vector memory.

## Generated/Implemented

- Updated `src/miminions/memory/sqlite.py`.
- Updated `tests/integration/test_sqlite_memory.py`.
- Updated `tests/integration/test_document_ingestion.py`.

## Verification

- Ran: `pytest -q tests/integration/test_distiller.py`
  - Result: 8 passed
- Ran: `pytest -q tests/integration/test_distiller.py tests/integration/test_document_ingestion.py tests/integration/test_sqlite_memory.py`
  - Result: 8 passed, 2 skipped
