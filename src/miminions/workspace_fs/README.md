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

Workspace/context tests plus `scripts/check_structure.py`.
Contract version: 1 (bump on any layout or bootstrap-file change).
