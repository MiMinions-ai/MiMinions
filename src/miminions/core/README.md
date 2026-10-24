# MiMinions Core

`miminions.core` is the package's domain core.

## Modules

| Module | What it provides |
|--------|------------------|
| `workspace.py` | The `Workspace` / `Node` / `Rule` model (`NodeType`, `RulePriority`), a JSON-backed `WorkspaceManager`, and resolver helpers (`resolve_workspace`, `ensure_workspace`). The rule condition engine is intentionally primitive (basic state matching). |
| `bootstrap.py` | `ensure_default_setup(config_dir)` — the idempotent first-run routine that creates a `default` workspace and a default agent record under `~/.miminions/`. |
| `auth.py` | `require_auth` — a decorator that gates CLI commands behind local sign-in (with an opt-in public-access bypass). |
| `gateway/` | A persistent server-runtime toolkit (message bus, channels, sessions, cron, orchestration). See [`gateway/README.md`](gateway/README.md). |

```python
from miminions.core.workspace import WorkspaceManager, resolve_workspace
from miminions.core.bootstrap import ensure_default_setup
from miminions.core.auth import require_auth
```

> `core/__init__.py` re-exports the **gateway** symbols only. Import workspace,
> bootstrap, and auth helpers from their submodules as shown above.

See the [Workspaces](https://miminions.ai/modules/workspaces/) and
[Gateway](https://miminions.ai/modules/gateway/) documentation for details.

## Contract

> [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md) — Contract v1.
> **Public surface:** gateway symbols via `core/__init__`; `WorkspaceManager/Workspace/Node/Rule`, `ensure_default_setup`, `require_auth` via submodules only (invariant: `__init__` re-exports gateway only).
> **State:** workspace JSON records (`WORKSPACE_SCHEMA_VERSION = 1` — bump + migrate on break).
> **Lifecycle:** idempotent first-run bootstrap under `~/.miminions/`; rule engine stays primitive by design.
> **Gate:** core/gateway tests + `scripts/check_structure.py`.
