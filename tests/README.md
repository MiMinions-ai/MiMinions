# MiMinions Tests

MiMinions uses a tiered test layout. The first directory answers how much of
the system is exercised; nested directories should answer which code or product
domain owns the behavior.

## Test Tiers

| Tier | Folder | Scope | Speed |
| --- | --- | --- | --- |
| **unit** | `tests/unit/` | One module or small abstraction; dependencies mocked or in-memory | Fast |
| **integration** | `tests/integration/` | Real interactions across modules, filesystem, CLI wiring, local stores, gateway services, or optional local dependencies | Seconds |
| **e2e** | `tests/e2e/` | Full user-facing flows through public entry points such as the packaged CLI | Slowest |

## Placement Rules

Every test path should answer two questions:

1. What kind of test is this? Use `unit`, `integration`, or `e2e`.
2. What domain owns this behavior? Use source-aligned names such as `cli`, `gateway`, `memory`, `session`, `task`, `tools`, `workflow`, or `workspace_fs`.

Prefer tier-plus-domain paths as the suite grows:

```text
tests/unit/cli/test_task.py
tests/unit/tools/test_mcp_adapter.py
tests/integration/cli/test_chat.py
tests/integration/gateway/test_services.py
tests/integration/memory/test_distiller.py
tests/e2e/cli/test_use_cases.py
```

Avoid adding new top-level domain folders directly under `tests/`. Keep domain
folders inside a tier so pytest selection remains predictable.

## Running Tests

```bash
# Unit tests
pytest tests/unit -v

# Integration tests
pytest tests/integration -v

# End-to-end tests
pytest tests/e2e -v

# Full suite
pytest tests/ -v

# Focused domain examples
pytest tests/unit/cli -v
pytest tests/integration/gateway -v

# Advisory coverage for CLI/workspace modules.
# First install dev test tooling:
#   python -m pip install -e ".[dev]"
python -m coverage run --source=miminions.cli,miminions.core.workspace,miminions.workspace_fs -m pytest tests/unit tests/integration
python -m coverage report -m --omit="*/miminions/cli/workflow.py"
```

## Current Structure

The active suite is currently organized primarily by tier:

```text
tests/
  unit/
  integration/
  e2e/
```

Some files are still flat within their tier, for example
`tests/integration/test_gateway_services.py`. That is allowed during migration,
but new or moved tests should prefer the tier-plus-domain form.

## Target Structure

Use this as the direction for gradual cleanup:

```text
tests/
  unit/
    agent/
    cli/
    core/
      gateway/
    data/
    memory/
    session/
    task/
    tools/
    utils/
    workflow/
    workspace_fs/

  integration/
    cli/
    gateway/
    memory/
    session/
    data/
    context/
    workspace_fs/

  e2e/
    cli/
    data/
```

## Migration Notes

- Move tests in small mechanical batches and run `pytest -q` after each batch.
- Keep behavior changes separate from file moves when practical.
- Prefer `tests/integration/cli/` for `CliRunner` tests that exercise command wiring, persistence, or filesystem behavior.
- Prefer `tests/unit/cli/` for command helper logic that can be tested with mocks and no real filesystem state.
- Prefer `tests/integration/gateway/` for async lifecycle, bus, channel, cron, and session-service interactions.
- Prefer `tests/unit/core/gateway/` for pure gateway dataclasses, simple helpers, or isolated model behavior.
- Keep end-to-end tests few and focused on complete user workflows.
