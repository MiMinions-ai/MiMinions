# 0004. Optional heavy dependencies behind extras

Date: 2026-07-13
Status: reconstructed (2026-09-01)

## Context

Even after the fastembed swap (ADR 0002), vector memory needs `fastembed`,
`sqlite-vec`, and `onnxruntime`. Most CLI usage — auth, agents, tasks,
workspaces, chat — never touches vector search. Making every user install ONNX
Runtime to run `miminions agent add` is a poor trade.

Before this change, importing anything that transitively reached `sqlite.py`
failed outright when those packages were absent.

## Decision

Move vector-memory dependencies into a `sqlite` extra (mirrored by `all`), and
make the imports in `memory/sqlite.py` conditional so the module can be imported
without them. Raise a clear install-instruction error only when the
functionality is actually used.

Committed as `feat(sqlite): make sqlite_vec and fastembed imports optional to
prevent import errors`. See `../reference/2026-07-13-optional-sqlite-deps.md`.

## Consequences

- Base install stays light; vector memory is opt-in via
  `pip install miminions[sqlite]`.
- **Every code path touching `SQLiteMemory` must tolerate its absence.** This is
  a standing constraint on new code, not a one-time change.
- Error messages carry install instructions, because a missing optional
  dependency is a user-facing condition rather than a bug.
- Tests that need vector memory guard with `pytest.importorskip("sqlite_vec")`.
  This is why a genuinely broken test can hide as a skip, as happened with the
  PDF ingestion fixture. Skips in this suite deserve suspicion.
- `pysqlite3` is preferred over the stdlib `sqlite3` because it reliably
  supports loadable extensions, which `sqlite-vec` requires. The stdlib module
  remains a fallback.
