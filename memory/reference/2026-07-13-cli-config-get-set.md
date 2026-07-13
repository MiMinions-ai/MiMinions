# Provenance Record: CLI `config get/set`

## Task

Add user-facing CLI commands to read/write top-level defaults in `config.json`:
`default_workspace` and `default_agent`.

## Sources

- Existing repository code only (no external web sources used).
- Direct references:
  - `src/miminions/cli/auth.py`
  - `src/miminions/core/workspace.py`
  - `src/miminions/cli/main.py`
  - `docs/modules/cli.md`

## Decisions

- Added new top-level command group `miminions config` with subcommands:
  - `miminions config get <key>`
  - `miminions config set <key> <value>`
- Restricted supported keys to explicit allowlist:
  - `default_workspace`
  - `default_agent`
- For `default_workspace`, `set` resolves workspace by id/prefix/name and stores canonical workspace id.
- For `default_agent`, `set` requires an existing agent id in `agents.json`.
- Kept `auth config` scope unchanged for auth-only flags (`public_access`, `auth_timeout`).

## Generated/Implemented

- New file `src/miminions/cli/config.py`.
- Updated command registration in `src/miminions/cli/main.py`.
- Added integration tests in `tests/integration/test_cli_config.py`.
- Updated docs in `docs/modules/cli.md`.

## Verification

- Ran: `pytest -q tests/integration/test_cli_config.py tests/integration/test_cli_init.py tests/test_bootstrap.py`
- Result: 11 passed, 1 warning (existing pytest config warning).
