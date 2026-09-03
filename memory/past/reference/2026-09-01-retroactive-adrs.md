# Retroactive ADRs and Future Tier

Date: 2026-09-01

Fourth and final record of the day. Completes the structure proposed in
`2026-09-01-memory-restructure.md`.

## External Sources

- None. Local repository files, git history, and user direction.

## Direct References

- `git log` filtered on refactor/migrate/switch/replace/remove/adopt.
- `git log -p --follow .github/workflows/python-app.yml`: lint gate evolution.
- `CHANGELOG.md` 0.1.0 through 0.4.1.
- `src/miminions/memory/sqlite.py`: pysqlite3 preference, fastembed model map.
- `src/miminions/cli/agent.py`, `cli/chat.py`, `cli/task.py`,
  `cli/execution.py`: `TODO` markers.
- `src/miminions/core/auth.py`: the `core -> cli` back-edge.

## Generated Parts

- `memory/past/adrs/README.md`: format, status vocabulary, index.
- Seven reconstructed ADRs, 0001 through 0007.
- `memory/future/roadmap.md`: four themes plus an explicit non-goals section.
- `memory/future/backlog.md`: nine items grouped by readiness, each with a
  trigger.
- `memory/INDEX.md` updated to reflect the populated tiers.

## Decisions

- Wrote seven ADRs, not more. The filter was whether a decision still constrains
  code today. Decisions that were later reversed, or that constrain nothing, were
  left in the timeline instead.
- Introduced a `reconstructed` status distinct from `accepted`, so readers can
  tell inferred reasoning from recorded reasoning. The decision is fact; the
  stated context is inference.
- Made every ADR's Consequences section carry the costs, not just the benefits.
  An ADR that only lists upsides is advocacy, not a record.
- Required a **trigger** on every backlog item. Items whose trigger is "already
  true" are actionable now; the rest are explicitly parked with the blocking
  condition named. This prevents the backlog becoming an undifferentiated wish
  list.
- Added an "Explicitly not planned" section to the roadmap, since knowing what
  was ruled out is as useful as knowing what is planned.
- Recorded the ADR 0005 amendment inline rather than as a superseding ADR,
  because the 2026-09-01 change moved the configuration's *location* without
  altering the decision.

## Findings

- **The narrow lint gate was a debt workaround, not a minimal-gate philosophy.**
  Three commits on 2026-08-24 tell the story: CI ran ruff defaults blocking;
  `bf00b37` added `--exit-zero` to stop failing on ~644 existing findings;
  `33a5ba8` reverted that and narrowed to `--select=E9,F63,F7,F82` instead. The
  choice was between an advisory broad gate and a blocking narrow one, and the
  blocking narrow one won. This is a better decision than it first appeared, and
  it reframes OQ-1: the debt is known and deliberately deferred.
- **The fastembed swap was safe only because model and dimensionality were held
  constant.** That makes the model name effectively load-bearing: changing it
  invalidates every stored embedding. Recorded as a constraint in ADR 0002.
- **The auth placeholder is the direct cause of the only import cycle.** ADR
  0006 links the two, so anyone implementing real auth sees that reversing the
  edge is part of the work.
- **`pytest.importorskip` in the sqlite tests is why a broken test could hide as
  a skip.** Noted in ADR 0004 as a standing reason to treat skips in this suite
  with suspicion.
- The `memory-*` CLI commands marked in `cli/agent.py` are the largest gap
  between library capability and CLI surface.

## Validation

- `uv run pytest -q`: 622 passed, 0 skipped.
- `uv run ruff check .`: clean.
- `uv build`: sdist and wheel for 0.4.1.
- `uv run --extra docs mkdocs build --strict`: built into `site/`.
- Editor diagnostics clean on all new memory files.
