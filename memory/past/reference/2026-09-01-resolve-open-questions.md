# Resolving OQ-1, OQ-2, OQ-5, OQ-6

Date: 2026-09-01

Third record of the day. Follows `2026-09-01-memory-structure-completion.md`,
which raised these four questions.

## External Sources

- None. Local repository files and user direction.

## Direct References

- `memory/future/open-questions.md`: OQ-1, OQ-2, OQ-5, OQ-6 as posed.
- `pyproject.toml`: dependency extras and tool configuration.
- `requirements.txt`: prior flat dependency list.
- `.github/workflows/python-app.yml`: CI definition.
- `tests/integration/data/test_document_ingestion.py`: fixture path.

## Decisions

User selected option 1 for OQ-1, OQ-2, and OQ-6, and approved OQ-5.

- **OQ-1** — moved the ruff rule set into `pyproject.toml` as `[tool.ruff]`
  (`line-length = 127`, `src = ["src", "tests"]`) and `[tool.ruff.lint]`
  (`select = ["E9", "F63", "F7", "F82"]`). The workflow now calls plain
  `ruff check --statistics src tests`.
- **OQ-2** — added `mkdocs build --strict` as a CI step and extended the CI
  install to `.[dev,sqlite,docs]`.
- **OQ-5** — `pyproject.toml` is now the sole source of dependency truth.
  `requirements.txt` was reduced to `-e .[all,dev,docs,cli-build]` plus a
  comment directing future additions to `pyproject.toml`.
- **OQ-6** — replaced the `.parent.parent.parent` chain with `parents[3]` and
  replaced the conditional `pytest.skip` with an assertion, so a missing fixture
  now fails loudly instead of silently skipping.

Chose to keep `requirements.txt` as a pointer rather than delete it, because
`pip install -r requirements.txt` is a common reflex and deleting a tracked file
is harder to reverse than neutering it.

## Generated Parts

- `[tool.ruff]` and `[tool.ruff.lint]` sections in `pyproject.toml`.
- `ruff` pinned `>=0.16.5` in the `dev` extra.
- `requirements.txt` rewritten as an extras pointer.
- CI install extended and a docs build step added.
- Fixture path and skip-to-assert change in `test_document_ingestion.py`.
- `open-questions.md` rewritten; OQ-7 added.
- `conventions.md` and `state.md` updated.

## Findings

- **Ruff version drift.** `requirements.txt` required `ruff>=0.16.5` while the
  `dev` extra left it unpinned, resolving to **0.15.20** — older than the
  documented floor. Lint behavior therefore depended on install method. Pinned
  `>=0.16.5` in `pyproject.toml`; the environment moved 0.15.20 -> 0.16.5.
- **The dead test passes.** `test_ingest_pdf` had never executed. On first run
  with the corrected path it passed, so the skip was hiding working code rather
  than a defect. Suite went from 621 passed / 1 skipped to 622 passed / 0
  skipped.
- **CI does not cover the integration branch.** The workflow triggers only on
  `main`, but `development` is where feature branches merge. Every merge into
  `development` is currently ungated. Filed as OQ-7 rather than changed,
  since altering trigger scope affects billing and review flow.
- `-e .` in a requirements file resolves relative to the working directory, not
  the file, so the pointer form requires running pip from the repository root.
  Verified acceptable; this matches standard pip behavior.

## Validation

- `uv run pytest -q`: 622 passed, 0 skipped.
- `uv run ruff check src tests`: clean. Bare `uv run ruff check .` also clean,
  confirming local and CI runs now agree.
- `uv build`: built sdist and wheel for 0.4.1.
- `uv run --extra docs mkdocs build --strict`: built into `site/`.
- `uv pip install -r requirements.txt --dry-run` in a throwaway 3.12
  environment: resolved `fastembed`, `sqlite-vec`, `mkdocs-material`,
  `pyinstaller`, and `ruff==0.16.5`, confirming all four extras are reachable.
