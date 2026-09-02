# Architecture

Verified 2026-09-01 against version 0.4.1.

`STRUCTURE.md` at the repository root is the canonical file map and public
import surface. This file covers what that map does not: layering, dependency
direction, and boundaries.

## Shape

A local-first Python package with a Click CLI front end. No server component is
required; persistent state is files under `~/.miminions`, relocatable via
`MIMINIONS_HOME`. There are 14 subpackages under `src/miminions/`.

## Observed dependency direction

Derived by scanning intra-package imports, not from intent:

```text
cli      -> agent context core memory session tools utils workflow workspace_fs
agent    -> context memory tools utils
context  -> core memory workspace_fs
memory   -> core session workspace_fs
core     -> cli utils workspace_fs
utils    -> session
session  -> workspace_fs
task     -> utils
data, tools, user, workflow, workspace_fs -> (no intra-package imports)
```

Layers, from the bottom up:

1. **Leaves** — `workspace_fs`, `tools`, `data`, `user`, `workflow`. No internal
   dependencies, so they are safe to import anywhere.
2. **Storage and support** — `session`, `utils`, `memory`, `core`.
3. **Composition** — `context`, `agent`, `task`.
4. **Front end** — `cli`.

`data`, `tools`, `user`, and `workflow` importing nothing internal means they
are either genuinely standalone or not yet integrated. `workflow` is the latter:
`STRUCTURE.md` records that it ships no CLI command group.

## Known layering violation

`core/auth.py` imports from `miminions.cli.auth`, making `core -> cli` a
back-edge against the direction every other module follows. It is the single
cycle in the graph.

The module docstring explains why it exists: authentication is a placeholder
for future account-backed features, `require_auth` is an identity decorator, and
the real predicates still live in the CLI layer. So it is deliberate and inert
rather than accidental, but it does mean `core` cannot be imported without
pulling in `cli`.

Not filed as an open question because it is documented and harmless today.
Worth revisiting if real auth is implemented, at which point the predicates
should move down into `core` and the CLI should import them upward.

## Persistence boundaries

- All persistent paths resolve through `miminions.core.paths.get_config_dir()`,
  honoring `MIMINIONS_HOME`. Nothing should hardcode `~/.miminions`.
- JSON stores go through `miminions.core.persistence` `load_json` / `save_json`,
  which write atomically and fail loudly on corrupt files.
- Chat transcripts are JSONL under `session/`.
- Vector memory is `SQLiteMemory` in `memory/sqlite.py`, gated behind the
  `sqlite` extra. Code paths must tolerate its absence.
- Workspace records carry `schema_version` (currently 1) with a load-time
  migration hook.

## Entry points

- Console script `miminions` -> `miminions.cli.main:main`.
- Module form `python -m miminions` -> `src/miminions/__main__.py`.
- Nine shipped command groups: `auth`, `agent`, `task`, `knowledge`,
  `workspace`, `execution`, `chat`, `gateway`, `prompt`.
