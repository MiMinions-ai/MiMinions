# MiMinions Interfaces

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).
> Contract version: 1. See the [package map and vocabulary](../../../STRUCTURE.md#package-ownership).

## Purpose

`miminions.interface` contains the CLI, first-run setup, user configuration,
and chat transcript helpers. It is broader than terminal presentation: some
runtime-building and persistence helpers currently live here too.

| Module | Responsibility |
|--------|----------------|
| [cli/](cli/README.md) | Click commands, user input/output, command dispatch, saved-record management and some runtime helpers. |
| [bootstrap.py](bootstrap.py) | Idempotent creation of a default workspace, agent record and configuration. |
| [config.py](config.py) | Configuration loading/validation and the `miminions config` command. |
| [session.py](session.py) | JSONL transcripts, session IDs, message-history conversion and turn-boundary trimming. |
| [gui/](gui/) | Empty reserved package; no GUI implementation is shipped here. |

Agent reasoning belongs to [core/agent](../core/agent/README.md), prompt and
memory processing to [core/context](../core/context/README.md), and durable
task scheduling to [system/execution](../system/execution/README.md).
However, execution handlers currently import some CLI-private helpers.
Do not assume the package boundary already enforces a one-way dependency.

## Public surface

The package root re-exports the transcript API:

```python
from miminions.interface import JsonlSessionStore, create_session_id
from miminions.interface.cli import cli
```

Use the concrete modules for `ensure_default_setup`, `load_config`, and
`trim_message_history`. The CLI console entry point is
`miminions.interface.cli.main:main`; the root package is not itself a CLI group.

## State

CLI records and configuration live under the config home (`~/.miminions/`,
overridden by `MIMINIONS_HOME`). Transcripts live at
`<workspace_root>/sessions/<session_id>.jsonl`, using
`core.workspace.WorkspaceLayout`.

A transcript records user/assistant text and metadata; it is not the execution
checkpoint. The prompt/chat handler prefers the native model-message checkpoint
in the execution store when available, otherwise reconstructing history from
the transcript. Memory distilled from a transcript is another separate artifact.
Gateway sessions use the distinct [daemon session API](../daemon/session.py).

## Lifecycle

Root help stays lazy. A real CLI subcommand triggers first-run setup, then
performs its operation or submits durable work. Transcript records are appended
during prompt/chat execution. History trimming preserves whole turns, including
tool call/return pairs. On chat exit, distillation is queued after submitted turns.

## Gate

`python -m pytest tests/unit/interface tests/integration/cli tests/integration/session`
and `python scripts/check_structure.py`.
