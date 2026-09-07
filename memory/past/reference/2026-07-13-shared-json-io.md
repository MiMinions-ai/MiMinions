# Provenance Record: Shared JSON IO Helper

## Task

Implement a global JSON helper based on bootstrap semantics and refactor bootstrap/config to use it.

## Sources

- Existing repository code only (no external web sources used).
- Direct references:
  - `src/miminions/core/bootstrap.py`
  - `src/miminions/cli/config.py`
  - `src/miminions/utils/__init__.py`

## Decisions

- Added shared helper module `src/miminions/utils/json_io.py`.
- Kept bootstrap-style defaults:
  - `load_json` returns `{}` when file is missing.
  - `save_json` is atomic by default.
  - malformed JSON raises `ValueError`.
- Added optional flexibility for callers:
  - `load_json(path, default=...)`
  - `save_json(..., ensure_parent=True, atomic=False)` when needed.
- Removed local JSON helper duplication in bootstrap and CLI config modules.
- Mapped helper `ValueError` to `click.ClickException` only at CLI boundary.

## Generated/Implemented

- New file `src/miminions/utils/json_io.py`.
- Updated `src/miminions/utils/__init__.py` exports.
- Refactored `src/miminions/core/bootstrap.py`.
- Refactored `src/miminions/cli/config.py`.
- Added tests in `tests/unit/test_json_io.py`.

## Verification

- Ran: `pytest -q tests/unit/test_json_io.py tests/integration/test_cli_config.py tests/integration/test_cli_init.py tests/test_bootstrap.py`
- Result: 15 passed, 1 warning (existing pytest config warning).
