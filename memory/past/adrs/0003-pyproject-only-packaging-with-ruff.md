# 0003. pyproject-only packaging with ruff

Date: 2026-06-25
Status: reconstructed (2026-09-01)

## Context

The project carried both `setup.py`/`setup.cfg` and `pyproject.toml`, plus
`flake8` for linting. Two packaging paths meant two places for metadata to
drift, and flake8 required its own config file and plugin set.

## Decision

Delete `setup.py` and `setup.cfg`, keeping `pyproject.toml` with the setuptools
build backend as the only packaging definition. Replace flake8 with ruff.

Committed as `replace flake8 with ruff for linting; remove setup.py and
setup.cfg`.

## Consequences

- `pyproject.toml` is the single packaging source of truth. This principle was
  extended to dependencies on 2026-09-01, when `requirements.txt` was reduced to
  a pointer at the extras.
- Ruff subsumes flake8's checks and runs fast enough to be non-negotiable in CI.
- Config placement was left unsettled by this decision: ruff ran on CLI flags
  with no `[tool.ruff]` section for over two months, which meant local runs and
  CI silently disagreed. Resolved on 2026-09-01. See ADR 0005.
- The build backend stays setuptools. Nothing here commits to that; it is
  simply what was already working.
