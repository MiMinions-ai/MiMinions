# Current State

Verified 2026-09-01 against version 0.4.1 on branch `development`.

## Health

| Signal | Status |
| --- | --- |
| Tests | 622 passed, 0 skipped |
| Lint | clean, exit 0 |
| Package build | builds sdist + wheel |
| Docs build (`--strict`) | builds into `site/` |
| Published release | 0.4.1 on PyPI |

All four are enforced in CI on `main`.

## Working

- Click CLI with nine shipped command groups: `auth`, `agent`, `task`,
  `knowledge`, `workspace`, `execution`, `chat`, `gateway`, `prompt`.
- Streaming replies via `Minion.run_stream()`, used by the CLI chat loop.
- Retries with exponential backoff, per-request timeouts, and `on_tool_call` /
  `on_turn_end` observability hooks surfaced by `chat start --verbose`.
- Message-history trimming at 40 messages, cutting only on user-turn boundaries
  so tool call/return pairs stay intact. On-disk transcript stays complete.
- Atomic JSON persistence with loud failure on corrupt files.
- `MIMINIONS_HOME` relocation of `~/.miminions`, resolved centrally through
  `core.paths`.
- Workspace schema versioning at v1 with a load-time migration hook.
- `SQLiteMemory` as a context manager, behind the `sqlite` extra.

## Partial or not integrated

- **`workflow`** — models and a controller exist, but no CLI command group is
  shipped and no other module imports it. Internal-only.
- **`user`** — a dataclass and a stub controller. No internal callers.
- **`data`** — a local content-addressable manager with no internal callers;
  reached only through the CLI knowledge path.
- **Authentication** — `core.auth.require_auth` is an identity decorator. The
  package is local-first and enforces nothing. Call-site shape is preserved for
  future work.

## Known broken

Nothing currently known broken.

Two latent defects were fixed on 2026-09-01, both of which had been invisible
because nothing exercised them: the PDF ingestion fixture path (the test had
always skipped) and the standalone CLI binary (it built successfully but
crashed on launch, and after that, every command group failed). See ADR 0008.

## Environment hazards

The project was moved from `~/Documents/dev/MiMinions`. Two stale artifacts
survived the move and were cleared on 2026-09-01:

- `.venv` console-script shebangs pointed at the old interpreter, breaking every
  entry point in `.venv/bin` while `uv run pytest` kept working. Symptom was
  `Failed to spawn: <script>`, which reads as a missing dependency.
- `__pycache__` bytecode embedded old absolute source paths, so pytest reported
  test locations as `../../../dev/MiMinions/tests/...`.

Both are cosmetic-to-fatal depending on the command, and neither is
self-announcing. If old paths reappear in output, clear `.venv` and
`__pycache__` before investigating further.

## Divergences between docs and reality

None currently recorded. The `requirements.txt` / `pyproject.toml` split was
reconciled on 2026-09-01, and CI now gates pull requests into `development` as
well as `main`.
