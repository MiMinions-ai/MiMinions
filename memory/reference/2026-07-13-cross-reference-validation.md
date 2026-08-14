# Provenance Record: Cross-reference validation for task/workflow agents

## Task

Prevent dangling references by validating that task/workflow agent references point to existing agents.

## Sources

- Existing repository code only (no external web sources used).
- Direct references:
  - `src/miminions/cli/task.py`
  - `src/miminions/cli/workflow.py`
  - `docs/modules/cli.md`

## Decisions

- `task add --agent <id>` now validates `<id>` exists in `agents.json`.
- `task update --agent <id>` now validates `<id>` exists before persisting.
- `workflow add --agents a,b,c` now validates all ids exist.
- `workflow update --agents ...` now validates all ids exist before update.
- Validation strategy is fail-fast with user-facing error output and no write.

## Generated/Implemented

- Updated `src/miminions/cli/task.py` with agent loader + validator.
- Updated `src/miminions/cli/workflow.py` with agent-list parser + validator.
- Added tests in `tests/integration/test_cli_task.py` and `tests/integration/test_cli_workflow.py`.
- Updated docs in `docs/modules/cli.md`.

## Verification

- Ran: `pytest -q tests/integration/test_cli_task.py tests/integration/test_cli_workflow.py tests/integration/test_cli_config.py`
- Result: 9 passed, 1 warning (existing pytest config warning).
