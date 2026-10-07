# Memory Structure Completion

Date: 2026-09-01

Follows `2026-09-01-memory-restructure.md`, which established the tiers.

## External Sources

- None. Based on local repository files, git history, and user direction.

## Direct References

- `CONTRIBUTING.md`: branching model and prerequisites, corrected.
- `STRUCTURE.md`: canonical file map, linked rather than duplicated.
- `CHANGELOG.md`: release contents and dates.
- `git log`, `git tag`: history reconstruction.
- `src/miminions/core/auth.py`: the `core -> cli` import.
- `tests/integration/data/test_document_ingestion.py`: fixture path.

## Generated Parts

- `memory/present/architecture.md`: layering, empirically derived dependency
  graph, persistence boundaries.
- `memory/present/state.md`: health signals, working/partial/broken inventory,
  environment hazards.
- `memory/present/glossary.md`: domain vocabulary.
- `memory/past/timeline.md`: milestones back to 2023 origin.
- Corrected the `CONTRIBUTING.md` branch table, branch rules, and the Python
  prerequisite (3.8 -> 3.12).
- Updated `open-questions.md`: closed OQ-3, added OQ-6.
- Cleared stale `__pycache__` directories outside `.venv`.

## Decisions

- Kept `architecture.md` complementary to `STRUCTURE.md` rather than
  overlapping. `STRUCTURE.md` owns the file map; memory owns layering and
  boundaries. Duplication would guarantee drift.
- Derived the dependency graph by scanning imports instead of describing
  intended architecture, because intent and reality had already diverged once.
- Recorded the `core -> cli` back-edge in `architecture.md` rather than as an
  open question, since the module docstring shows it is deliberate and inert.
- Did **not** fix the PDF fixture path. It activates a never-run test whose
  outcome is unknown; filed as OQ-6 for a deliberate decision.
- Marked pre-tag timeline entries as inferred, keeping the append-only tier
  honest about confidence.

## Findings

- **Layering cycle.** `core/auth.py` imports `miminions.cli.auth`, the only
  back-edge in the graph. Deliberate: auth is a placeholder and `require_auth`
  is an identity decorator.
- **Dead PDF coverage.** `test_ingest_pdf` resolves its fixture three `.parent`
  hops up to `tests/examples/example_files/resume.pdf`, which does not exist.
  The fixture is at `examples/example_files/resume.pdf`, four hops up. The test
  has always skipped, so PDF ingestion is untested.
- **Second relocation artifact.** `__pycache__` bytecode retained old absolute
  source paths, making pytest report skips as
  `../../../dev/MiMinions/tests/...`. Cleared; paths now report correctly. This
  is distinct from the stale `.venv` found earlier and did not appear until the
  venv was fixed.
- **Four subpackages have no internal callers**: `data`, `tools`, `user`,
  `workflow`. For `workflow` and `user` this reflects incompleteness.
- **`CONTRIBUTING.md` had two errors**, not one: the branching model and a
  Python 3.8 prerequisite contradicting `requires-python = ">=3.12"`.

## Validation

- `uv run pytest -q -rs`: 621 passed, 1 skipped; skip path now reports relative
  to the correct root.
- Markdown lint on `CONTRIBUTING.md`: the MD037 warning introduced by the new
  branch table was fixed with backticks. Remaining warnings in that file are
  pre-existing and untouched.
