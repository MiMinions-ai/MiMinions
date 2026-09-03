# Roadmap

Themes and outcomes, no dates. A theme earns a place here only if it changes
what the project *is*, not just what it does.

Derived on 2026-09-01 from in-code markers, changelog signals, and the state
inventory. Nothing here is committed work.

## Theme: close the gap between what ships and what is implied

The project's most consistent recent motion — visible across 0.4.1 and the
2026-09-01 audit — is removing surfaces that promised more than they delivered:
the no-op `--async` flag, keyword-based demo tool routing, docs implying a
`miminions workflow` command, a test that had never run.

Outcome: every public surface either works or does not exist. No placeholders
visible to users.

Remaining instances are inventoried in `../present/state.md` under "Partial or
not integrated": `workflow`, `user`, and `data` have no internal callers, and
`require_auth` enforces nothing.

## Theme: memory as a first-class CLI surface

`SQLiteMemory` and the markdown store are reachable from the Python API and
implicitly through agent tools, but there is no direct CLI surface for them.
`cli/agent.py` carries an explicit marker for `memory-attach`,
`memory-store` / `memory-recall` / `memory-update` / `memory-delete`, and
`ingest-document`.

Outcome: a user can inspect and manipulate agent memory without writing Python.

This is the largest capability currently present in the library but absent from
the CLI.

## Theme: decide the fate of the unintegrated subpackages

`workflow` has models, a controller, and trace types, but ships no command group
and nothing imports it. `user` is a dataclass and a stub. `data` is reachable
only via the knowledge path.

Outcome: each is either integrated, or removed and its ADR marked superseded.
Carrying them indefinitely costs comprehension on every read of the tree.

## Theme: make the quality gates mean something

ADR 0005 records a deliberately narrow lint gate chosen over an advisory broad
one. The stylistic debt it sidesteps is untracked and not shrinking. CI does not
run against the integration branch (OQ-7).

Outcome: gates that run where merges happen, over a rule set that grows on
purpose rather than by accident.

## Explicitly not planned

- A server, daemon, or hosted control plane. ADR 0007 commits to local-first
  file state; reversing that is a different product.
- Replacing pydantic-ai. ADR 0001 notes the agent layer is small precisely
  because it delegates. Owning the model loop is a large cost for unclear gain.
