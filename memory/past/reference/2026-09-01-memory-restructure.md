# Memory Restructure and Toolchain Verification

Date: 2026-09-01

## External Sources

- None. Based on local repository files, git state, and user direction.

## Direct References

- `memory/reference/`, `memory/adrs/`, `memory/external/`: pre-existing memory
  directories, relocated.
- `.github/workflows/python-app.yml`: CI lint, test, and build definition.
- `pyproject.toml`: packaging metadata and optional dependency extras.
- `requirements.txt`: flat dependency list containing `mkdocs-material>=9.5.32`.
- `CONTRIBUTING.md`: documented branching model.
- `mkdocs.yml`: MkDocs Material site configuration.
- `memory/past/reference/2026-08-24-release-0.4.0-prep.md`: prior record showing
  `mkdocs build --strict` succeeding.

## Generated Parts

- Restructured `memory/` into `past/`, `present/`, and `future/` tiers.
  Relocated `reference/` with `git mv` to preserve history; moved the empty
  `adrs/` and `external/` directories under `past/`.
- Added `memory/INDEX.md` describing the tiers, the five durability rules, the
  graduation path, and source-of-truth boundaries.
- Added `memory/present/conventions.md` with verified commands.
- Added `memory/future/open-questions.md` with OQ-1 through OQ-5.
- Added a `docs` extra to `pyproject.toml` carrying `mkdocs-material>=9.5.32`.
- Recreated `.venv` to repair stale interpreter paths.

## Decisions

- Chose three horizon-based tiers over a flat directory so that append-only
  history is structurally separated from mutable present-state. Mixing them was
  judged the main cause of documentation rot.
- Recorded only commands observed to succeed. Anything unverified was filed as
  an open question rather than written as fact.
- Declared `mkdocs-material` as a `docs` extra in `pyproject.toml` rather than
  installing it ad hoc, because it was already declared in `requirements.txt`
  and the omission from extras was the actual defect.
- Kept `requirements.txt` unchanged; reconciling it with `pyproject.toml` is
  filed as OQ-5 rather than done opportunistically.
- Left the ruff configuration in the workflow rather than moving it into
  `pyproject.toml`, since that changes local lint behavior and warrants an
  explicit decision. Filed as OQ-1.

## Findings

- The ruff rule set was not missing; it lives as CLI flags in the CI workflow
  (`--select=E9,F63,F7,F82 --line-length=127` over `src tests`) and passes
  clean. A bare `ruff check .` uses defaults and reports 644 unrelated findings,
  which does not reflect CI.
- `mkdocs` failing with `Failed to spawn` was not a missing dependency. `.venv`
  script shebangs pointed at `/Users/shengxio/Documents/dev/MiMinions/.venv/bin/python`,
  the project's location before it was moved. Console scripts were broken while
  `uv run pytest` continued to work, masking the fault.
- `uv run` prunes extras not named on the invocation, so docs commands require
  an explicit `--extra docs`.
- Test count rose from 609 passed / 2 skipped to 621 passed / 1 skipped after
  the venv rebuild, because the `sqlite` extra resolved correctly.
- `CONTRIBUTING.md` describes `master` and `develop`; neither exists. The remote
  default is `main` and local work happens on `development`.

## Validation

- `uv run pytest -q`: 621 passed, 1 skipped.
- `uv run ruff check --line-length=127 --statistics --select=E9,F63,F7,F82 src tests`:
  clean, exit 0.
- `uv build`: built `dist/miminions-0.4.1.tar.gz` and the matching wheel.
- `uv run --extra docs mkdocs build --strict`: built into `site/` in 0.56s.
- `git status` confirms the reference records moved as renames, preserving
  history.
