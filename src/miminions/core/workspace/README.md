# Workspace FS (On-Disk Workspace Layout)

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).
> This module defines the Level-3 (workspace) contract. `core.workspace` owns the node/rule graph; this module owns the files.

## Purpose

Define and scaffold the standard workspace directory layout, and read it
back for prompt assembly. Owns paths and bootstrap file contents; never
owns workspace graph semantics (`core`) or memory meaning (`memory`).

## Public surface

```python
from miminions.workspace_fs import (
    WorkspaceLayout, BOOTSTRAP_PROMPT_FILES, init_workspace,
    read_prompt_files, read_memory_md, list_skills, read_skill,
)
```

Layout: `root/{prompt,memory,skills,sessions,data}/`.
`BOOTSTRAP_PROMPT_FILES = [AGENTS.md, USER.md, TOOLS.md, IDENTITY.md]`.

## State

The workspace directory itself. Bootstrap templates scaffold
`prompt/*.md`, `memory/MEMORY.md` (Facts/Decisions/Preferences),
`memory/HISTORY.md` (append-only), and `skills/core/SKILL.md`. Markdown
files are the source of truth; readers return `""`/omit missing files
rather than failing.

## Lifecycle

`init_workspace()` scaffolds idempotently → agent sessions append under
`sessions/` and `data/` → `ContextBuilder` consumes via the readers each
run. Layout changes are breaking: bump the version and migrate existing
workspaces explicitly.

## Gate

The internal `discovery.py` scanner reads workspace Python ASTs, README excerpts,
and manifests without importing project code. It honors nested `.gitignore` rules,
always excludes dependency/state/build/cache directories, and skips symlinks and
Windows junctions. Limits are 10,000 entries and 1 MiB per inspected file. File
content digests and a scanner version key a rebuildable JSON metadata cache under
the associated state workspace; atomic writes permit concurrent scans. Discovery
adds no project files and does not change the standard L3 directory layout.

Only public unconditional top-level plain functions are eligible. Methods,
decorators, generators, tests, positional-only/variadic parameters, unsupported
types, executable defaults, and subsequent rebinding are excluded. Supported
inputs include JSON primitives, typed lists, string-keyed dictionaries, nullable
unions, and literal defaults. Unannotated required inputs use strings; optional
inputs infer from their default (a None default accepts string or None).

Workspace/context tests plus `scripts/check_structure.py`.
Contract version: 1 (bump on any layout or bootstrap-file change).
