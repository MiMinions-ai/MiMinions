# Session (JSONL Transcript Store)

> Contract: [Recursive, Bounded Evolution](../../../docs/architecture/recursive-evolution.md).

## Purpose

Persist chat transcripts as append-only JSONL so any session can be
resumed with full context. Owns transcript storage and history trimming;
never owns memory distillation (that is `memory`) or prompt assembly
(that is `context`).

## Public surface

```python
from miminions.session import JsonlSessionStore, create_session_id
```

## State

One `.jsonl` file per session under `<workspace_root>/sessions/`
(see `workspace_fs.WorkspaceLayout.sessions_dir`). The transcript is the
source of truth for what was said; distilled facts derived from it live
in `memory`, never the reverse.

## Lifecycle

Append during chat → on resume, replay as native `pydantic_ai` messages →
`trim_message_history()` caps history (default 40 messages) cutting only
at turn boundaries (`ModelRequest` with `UserPromptPart`) so tool
call/return pairs are never split. On exit, `MemoryDistiller` reads the
transcript and promotes facts one level up.

## Gate

Session/chat integration tests (`pytest tests/integration/cli/test_chat.py`
and session tests) plus `scripts/check_structure.py`. Contract version: 1.
