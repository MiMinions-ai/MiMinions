# MiMinions Memory

Durable project memory for humans and agents. Read this file first, then load
only the tier you need.

## Layout

| Path | Horizon | Answers | Churn |
| --- | --- | --- | --- |
| `past/` | Past | Why is the code this way? | Append-only, never edited |
| `present/` | Present | What is true right now? | Rewritten on change |
| `future/` | Future | Where are we going? | Rewritten; items graduate to `past/` |

### `past/` — append-only

- `past/adrs/` — one architectural decision per file, `NNNN-title.md`.
  Superseding a decision means adding a new file with a `Supersedes: NNNN`
  header. Never edit an accepted ADR. See `past/adrs/README.md` for the format
  and index. Eight ADRs; 0001-0007 reconstructed on 2026-09-01, 0008 written
  contemporaneously.
- `past/reference/` — per-change provenance records, `YYYY-MM-DD-slug.md`.
  Each records external sources, direct references, generated parts, decisions,
  and validation.
- `past/external/` — dated observations of open-source projects close to
  MiMinions: upstreams we depend on, alternatives we chose against, and adjacent
  projects we are compared to. See `past/external/README.md` for scope and the
  rule that nothing unverified may be recorded as fact.
- `past/timeline.md` — one line per release or milestone, newest first.

### `present/` — rewritten in place

- `present/conventions.md` — verified build, test, and lint commands plus code
  style rules.
- `present/architecture.md` — module map, data flow, and boundaries.
- `present/state.md` — what works, what is partial, what is known-broken.
- `present/glossary.md` — domain vocabulary.

### `future/` — cheapest to change

- `future/roadmap.md` — themes and outcomes, no dates.
- `future/backlog.md` — candidate work, each with a "why now" trigger. An item
  without a trigger is not ready to be picked up.
- `future/open-questions.md` — unresolved forks; each graduates into an ADR.

## Rules

1. Nothing in `past/` is ever edited. Correct it by appending.
2. Every claim in `present/` must be verifiable. Anything unverified belongs in
   `future/open-questions.md`.
3. Link both directions: an ADR links forward to the reference record that
   implemented it, and the record links back.
4. Graduation path: open question -> ADR -> reference record -> timeline entry.
5. Keep this file plus `present/` under roughly 400 lines total (currently 379).
   Depth lives in `past/`, read on demand. If the tier outgrows the budget,
   move detail down into `past/` rather than raising the ceiling again.

## Source-of-truth boundaries

Memory describes and links; it does not duplicate. Canonical sources stay where
they are:

- `pyproject.toml` — dependencies, entry points, package metadata.
- `CHANGELOG.md` — released version history.
- `STRUCTURE.md` — repository file map.
- `docs/` — user-facing documentation.
