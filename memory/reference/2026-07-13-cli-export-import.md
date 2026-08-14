# Provenance Record: CLI `export` / `import`

## Task

Add simple JSON backup and restore workflow for agents/tasks/knowledge to enable cross-machine migration.

## Sources

- Existing repository code only (no external web sources used).
- Direct references:
  - `src/miminions/cli/main.py`
  - `src/miminions/cli/config.py`
  - `docs/modules/cli.md`

## Decisions

- Added top-level commands:
  - `miminions export --output <path>`
  - `miminions import --input <path> --mode merge|replace`
- Export payload includes:
  - `version`
  - `exported_at`
  - `agents`
  - `tasks`
  - `knowledge`
- Import supports two behaviors:
  - `merge`: keep existing and overlay imported ids
  - `replace`: overwrite each target store with imported payload for that section

## Generated/Implemented

- New command module: `src/miminions/cli/transfer.py`.
- CLI registration updates in `src/miminions/cli/main.py`.
- Integration tests in `tests/integration/test_cli_transfer.py`.
- Docs updates in `docs/modules/cli.md`.

## Verification

- Ran: `pytest -q tests/integration/test_cli_transfer.py tests/integration/test_cli_config.py tests/integration/test_cli_init.py`
- Result: 9 passed, 1 warning (existing pytest config warning).
