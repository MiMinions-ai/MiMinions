# Open Questions

Unresolved forks. Each should graduate into an ADR in `../past/adrs/` once
decided, or be deleted if it stops mattering.

Resolved items are summarized in `../past/timeline.md` and the reference records
for the date they were decided.

## OQ-9: Should the PyInstaller flag list have a single source?

Resolved 2026-09-01, option 1. Build settings moved into a committed
`miminions-cli.spec`; both `deploy/build_cli.sh` and the `cli-binary` CI job now
call `pyinstaller --clean miminions-cli.spec`. The stale auto-generated spec
referencing a deleted `main.py` was replaced, and `.gitignore` carries a
`!miminions-cli.spec` negation. See ADR 0008.

## OQ-4: Populate the adjacent-projects section of the external landscape

`past/external/` now has a format and an index seeded from verified dependency
facts. The **adjacent projects** section is deliberately empty: naming
competitors from memory would breach the rule that nothing unverified is
recorded as fact.

Needs a deliberate pass with sources. Axes suggested in
`past/external/landscape.md`: local-first CLI agents vs. hosted platforms,
frameworks built on pydantic-ai, and vector-memory-over-SQLite tools.

Blocked on: research time, not on a decision.
