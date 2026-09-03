# Conventions

Every command below was run in this repository and observed to work. Last
verified 2026-09-01 against version 0.4.1.

## Toolchain

`uv` drives everything. Python `>=3.12` is required by `pyproject.toml`.

| Task | Command | Observed result |
| --- | --- | --- |
| Sync environment | `uv sync --extra dev --extra sqlite --extra docs` | full toolchain |
| Run tests | `uv run pytest -q` | 622 passed |
| Lint | `uv run ruff check src tests` | clean, exit 0 |
| Build package | `uv build` | builds sdist + wheel into `dist/` |
| Build docs | `uv run --extra docs mkdocs build --strict` | builds into `site/` |
| Dependency tree | `uv tree` | resolves cleanly |

Validation order is build/tests first, then linting.

## Linting

Ruff is configured in `pyproject.toml` under `[tool.ruff]` and
`[tool.ruff.lint]`: line length 127, selecting `E9`, `F63`, `F7`, `F82`
(syntax errors and undefined names). CI invokes plain `ruff check --statistics
src tests` and picks up the same settings.

A bare `ruff check .` now agrees with CI. Before 2026-09-01 the rule set lived
only as CLI flags in the workflow, so local runs silently fell back to ruff
defaults and reported hundreds of unrelated findings.

`ruff` is pinned `>=0.16.5` because rule behavior varies across versions.

## Dependencies

`pyproject.toml` is the single source of truth. `requirements.txt` is a thin
pointer (`-e .[all,dev,docs,cli-build]`) kept only so `pip install -r
requirements.txt` from the repository root still works. Never add packages to
`requirements.txt`.

## Environment gotcha: stale venv after a move

`.venv` hardcodes absolute paths in console-script shebangs. This project was
relocated from `~/Documents/dev/MiMinions`, which left every entry point in
`.venv/bin` pointing at a nonexistent interpreter, surfacing as
`error: Failed to spawn: <script>` — which reads as a missing dependency.
`uv run pytest` kept working, masking it. Confirm with
`head -1 .venv/bin/<script>`; fix by deleting `.venv` and re-syncing. Stale
`__pycache__` outside `.venv` caused the same confusion in pytest paths.

## Optional extras

| Extra | Purpose |
| --- | --- |
| `sqlite` | `fastembed`, `sqlite-vec` for vector memory |
| `all` | same as `sqlite` |
| `dev` | `pytest`, `pytest-asyncio`, `pytest-cov`, `ruff`, `build` |
| `docs` | `mkdocs-material` for the MkDocs site |
| `cli-build` | `pyinstaller` for the packaged CLI binary |

`uv run` prunes extras not named on the command line, so docs commands need an
explicit `--extra docs`. `deploy/build_cli.sh` runs `uv sync --extra cli-build`,
which prunes the others: re-sync with the full list afterwards or the test suite
silently drops to 609 passed / 2 skipped as the `sqlite` extra disappears.

## Test configuration

From `pyproject.toml`:

- `asyncio_mode = "auto"` — async tests need no explicit marker.
- `testpaths = ["tests"]`.

## Entry points

- Console script: `miminions` -> `miminions.cli.main:main`.
- Module form: `python -m miminions`.

## Code style

Governed by the project instruction set, which is the source of truth: simple
control flow, statically bounded loops, no post-init allocation, functions under
roughly 60 logical lines, at least two assertions per function on average,
narrowest variable scope, all return values checked and inputs validated, no
metaprogramming. Combine context managers as `with (a, b):`.

## Branching

`main` is the stable default; `development` is the integration branch. Work
branches use `<type>/<ticket>-<description>`: `feature/*`, `fix/*`, and
`enhance/*` off `development`, `hotfix/*` off `main`, `release/*` optional.

While the team is small, `development` merges directly into `main` to cut a
release; a `release/*` branch is used only when a release needs stabilising
apart from ongoing work.

`CONTRIBUTING.md` was corrected on 2026-09-01 (it described a `master`/`develop`
model that never existed) and again on 2026-09-02, replacing an unused `bug/*`
prefix with the `fix/*` and `enhance/*` prefixes actually in use.

## Continuous integration

`.github/workflows/python-app.yml` runs on push to `main` and on pull requests
targeting `main` or `development`, on Python 3.12, installing with
`pip install -e ".[dev,sqlite,docs]"`, then: pytest, `python -m build`,
`ruff check --statistics src tests`, and `mkdocs build --strict`.

`python-publish.yml` runs on release publication:

- `build` (ubuntu) produces the single `py3-none-any` wheel.
- `verify` installs that wheel with `[all]` on ubuntu/macOS/Windows and smoke
  tests it. `publish` depends on this.
- `cli-binary` builds the PyInstaller executable once per OS, because that
  artifact genuinely cannot be cross-built, and `attach-binaries` uploads all
  three to the release.
- `publish` uploads the wheel to PyPI via trusted publishing.

The PyInstaller flags are load-bearing and duplicated between the workflow and
`deploy/build_cli.sh`. See `../past/adrs/0008-cli-binary-build-flags.md` and
`../future/open-questions.md` OQ-9.

## Provenance

Implementation work records a dated file in `../past/reference/` covering
external sources, direct references, generated parts, decisions, and validation.
