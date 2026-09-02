# 0006. Authentication as an inert placeholder

Date: 2026-08-25
Status: reconstructed (2026-09-01)

## Context

Earlier versions carried "complex user authentication and validation systems"
(removed in 0.3.0). But MiMinions is a local-first CLI operating on the user's
own files with the user's own API keys. There is no server, no multi-tenancy,
and nothing to authenticate against.

Removing auth entirely would mean deleting `@require_auth` from every command
and re-adding it later if account-backed features ever arrive.

## Decision

Keep `require_auth` as an identity decorator that returns the function
unchanged, and keep the call sites. Consolidate the real predicates
(`is_authenticated`, `is_public_access_enabled`) in `cli/auth.py`, with
`core/auth.py` re-exporting.

Committed as `Refactor authentication handling across CLI modules to use
placeholder decorators for future account-backed features`.

## Consequences

- No command is blocked. The package requires no sign-in.
- The call-site shape is preserved, so enabling real auth later is a change to
  one decorator rather than to every command.
- **This creates the only cyclic import in the package.** `core/auth.py` imports
  from `miminions.cli.auth`, a `core -> cli` back-edge against the direction
  every other module follows. `core` cannot be imported without pulling in
  `cli`.
- The cycle is tolerable only because the decorator is inert. If real auth is
  implemented, the predicates should move down into `core` and the CLI should
  import upward, reversing the edge.
- A decorator that looks like a security control but enforces nothing is a
  hazard if misread. The module docstring exists to prevent that and should be
  kept accurate.
