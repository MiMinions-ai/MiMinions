# 0005. Narrow blocking lint gate over broad advisory one

Date: 2026-08-24
Status: accepted (reconstructed 2026-09-01; amended 2026-09-01)

## Context

When ruff replaced flake8 (ADR 0003), CI ran `ruff check --line-length=127 src
tests` with the default rule set, blocking on failure. The codebase did not
satisfy ruff's defaults; roughly 644 findings existed, most of them stylistic.

On 2026-08-24 this came to a head, and two options were tried in sequence:

1. `bf00b37` added `--exit-zero`, keeping the broad rule set but making the step
   advisory. CI went green while reporting hundreds of findings nobody acted on.
2. `33a5ba8` reverted that and instead narrowed to
   `--select=E9,F63,F7,F82`, restoring a blocking gate over a much smaller rule
   set.

## Decision

Keep option 2: a **blocking** gate over a **narrow** rule set — syntax errors
(`E9`) and undefined or misused names (`F63`, `F7`, `F82`) — rather than an
advisory gate over a broad one.

The reasoning is that a lint step which cannot fail teaches everyone to ignore
lint. A small set of rules that always holds is worth more than a large set that
never blocks anything.

## Amendment, 2026-09-01

The rule set was moved from CLI flags in `.github/workflows/python-app.yml` into
`[tool.ruff]` and `[tool.ruff.lint]` in `pyproject.toml`. The selection itself
is unchanged. `ruff` was pinned `>=0.16.5`, since rule behavior varies by
version and an unpinned `dev` extra had been resolving to 0.15.20.

This closes the gap where a local `ruff check .` used ruff defaults and
disagreed with CI.

## Consequences

- The gate catches real errors — undefined names, syntax breakage — and nothing
  cosmetic.
- **The stylistic debt still exists.** It is not tracked, not shrinking, and
  invisible under the current selection. Widening the rule set later means
  confronting it in one pass.
- Because configuration now lives in `pyproject.toml`, widening is a one-line
  change, which makes an incremental approach (adding rule families one at a
  time) practical in a way it was not before.
