# Provenance Record: CLI `--json` output flag for list/show

## Task

Add machine-readable JSON output for list/show command surfaces to support scripting.

## Sources

- Existing repository code only (no external web sources used).
- Direct references:
  - `src/miminions/cli/agent.py`
  - `src/miminions/cli/task.py`
  - `src/miminions/cli/knowledge.py`
  - `src/miminions/cli/workspace.py`
  - `src/miminions/cli/execution.py`
  - `docs/modules/cli.md`

## Decisions

- Added `--json` flags while preserving current human-readable default output.
- Implemented on key list/show commands:
  - `agent list/show`
  - `task list/show`
  - `knowledge list/show`
  - `workspace list/show`
  - `execution session list`
  - `execution interaction list/show`
- Kept `execution interaction show` behavior JSON by default (existing precedent), with `--json` accepted for consistency.

## Generated/Implemented

- Updated CLI command modules listed above.
- Added tests in domain files:
  - `tests/integration/test_cli_agent.py`
  - `tests/integration/test_cli_task.py`
  - `tests/integration/test_cli_knowledge.py`
  - `tests/integration/test_cli_workspace_commands.py`
  - `tests/integration/test_cli_execution.py`
- Updated docs in `docs/modules/cli.md` command tables.

## Verification

- Ran: `pytest -q tests/integration/test_cli_agent.py tests/integration/test_cli_task.py tests/integration/test_cli_knowledge.py tests/integration/test_cli_execution.py tests/integration/test_cli_workspace_commands.py tests/integration/test_cli_workflow.py tests/integration/test_cli_config.py`
- Result: 30 passed, 1 warning (existing pytest config warning).
