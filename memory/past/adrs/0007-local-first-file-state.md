# 0007. Local-first file state under MIMINIONS_HOME

Date: 2026-08-24
Status: reconstructed (2026-09-01)

## Context

Agents, workspaces, sessions, and configuration all need to persist. A database
server would be operationally heavy for a CLI tool. Paths were being constructed
ad hoc against `~/.miminions`, which made the location impossible to override
for testing, sandboxing, or running multiple profiles.

## Decision

Persist everything as files under a single state directory, resolved centrally
through `miminions.core.paths.get_config_dir()` and overridable with the
`MIMINIONS_HOME` environment variable. Default remains `~/.miminions`.

Shipped in 0.4.0 alongside atomic JSON persistence
(`miminions.core.persistence`) and workspace schema versioning.

## Consequences

- No server, no daemon, no external database. Install and run.
- **Nothing may hardcode `~/.miminions`.** All paths go through
  `get_config_dir()`, or the override silently fails to apply.
- Tests and parallel profiles can relocate state by setting one variable.
- JSON stores are written atomically and fail loudly on corruption, because a
  half-written file in the user's home directory is worse than an error.
- Persisted records carry `schema_version` (currently 1) with a load-time
  migration hook. Unversioned records are treated as v1 and stamped on next
  save. See `../reference/2026-07-13-cli-export-import.md` and the 0.4.0 release
  notes.
- Chat transcripts are append-only JSONL, kept complete even when the model's
  context window is trimmed. The transcript is the record; the context is a
  view of it.
