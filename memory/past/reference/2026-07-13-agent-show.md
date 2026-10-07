# Provenance Record: CLI `agent show`

## Task

Add `miminions agent show <id>` style command for parity with task/knowledge/workspace,
with flexible lookup by id, id prefix, or exact agent name.

## Sources

- Existing repository code only (no external web sources used).
- Direct references:
  - `src/miminions/cli/agent.py`
  - `tests/integration/test_cli_agent.py`
  - `docs/modules/cli.md`

## Decisions

- Added `agent show <agent_ref>` command.
- `agent_ref` resolution order:
  - exact id
  - id prefix
  - exact name
- Added ambiguity handling with explicit error output listing matches.
- Kept existing command style (`click.echo` + return) for not-found/ambiguous cases.

## Generated/Implemented

- Updated `src/miminions/cli/agent.py`.
- Added tests in `tests/integration/test_cli_agent.py`:
  - show by exact id
  - show by id prefix
  - show by exact name
- Updated docs in `docs/modules/cli.md`.

## Verification

- Ran: `pytest -q tests/integration/test_cli_agent.py`
- Result: 25 passed, 1 warning (existing pytest config warning).
