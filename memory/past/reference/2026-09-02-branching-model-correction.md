# Branching Model Correction

Date: 2026-09-02

Second correction to `CONTRIBUTING.md`; follows the 2026-09-01 fix that replaced
a `master`/`develop` model with `main`/`development`.

## External Sources

- None. Local branch inventory and user direction.

## Direct References

- `CONTRIBUTING.md`: branch table and rules.
- `git branch -a`: live branch prefix inventory.
- `.github/workflows/python-app.yml`: CI trigger scope.

## Decisions

- Added `enhance/*` as a documented prefix for improvements to things that
  already work (docs, tooling, refactors), per user direction.
- Replaced the documented `bug/*` prefix with `fix/*`.
- Documented that `development` merges directly into `main` to cut a release
  while the team is small, with `release/*` reserved for when a release needs
  stabilising apart from ongoing work.
- Left the Conventional Commits type list untouched. Commit types and branch
  prefixes are separate vocabularies, and `enhance` is not a Conventional
  Commits type; `refactor`, `docs`, and `chore` already cover that work.

## Findings

**`bug/*` had never been used.** The live inventory shows `feature/` 19,
`fix/` 7, `hotfix/` 6, `enhance/` 2, `release/` 2, and zero `bug/`.

This was my own error from 2026-09-01. When correcting the `master`/`develop`
table I carried the original's `bug-*` forward as `bug/*` without checking
usage, having verified only the merge-commit prefixes rather than the full
branch list. The documented convention was wrong in a new way for a day.

Recording it because the lesson generalises: correcting a document against
reality means checking *every* claim in it, not just the one that prompted the
correction.

## Generated Parts

- `CONTRIBUTING.md`: branch table rewritten with one row per prefix and a
  purpose for each; examples updated; new "Promoting to main" subsection.
- `memory/present/conventions.md`: branching section updated; stale claim that
  `main` is "the only CI trigger" removed, since pull requests into
  `development` have been gated since 2026-09-01.
- `memory/present/conventions.md`: code style list compressed from a nine-item
  list to a prose sentence pointing at the instruction set, to stay within the
  eager-load budget.

## Validation

- Branch prefix counts taken from `git branch -a` across local and remote refs.
- Memory eager-load budget: 397 lines against a 400 ceiling, down from 403
  immediately after the branching edit.
- Markdown lint on `CONTRIBUTING.md`: no new warnings. The remaining MD012,
  MD031, MD032, MD040, and MD047 warnings predate this change and were left
  alone.
