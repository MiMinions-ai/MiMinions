# Timeline

One line per milestone, newest first. `CHANGELOG.md` remains the canonical
record of what changed in each release; this file records *when* and *why*, plus
milestones that never appeared in a release.

Reconstructed from git history and tags on 2026-09-01. Entries before the first
tag are inferred from commit clusters and should be treated as approximate.

## 2026-09-01 — Project memory established, toolchain consolidated

`memory/` restructured into past/present/future tiers. Toolchain verified end to
end. Repository relocation fallout (stale venv, stale bytecode) cleared.

Four decisions followed from what the audit surfaced: ruff configuration moved
from CI flags into `pyproject.toml` so local and CI lint agree; docs added to
the CI gate; `pyproject.toml` made the sole dependency source with
`requirements.txt` reduced to a pointer; and a fixture-path bug fixed that had
kept PDF ingestion untested since it was written.

See `reference/2026-09-01-memory-restructure.md`,
`reference/2026-09-01-memory-structure-completion.md`, and
`reference/2026-09-01-resolve-open-questions.md`.

## 2026-08-31 — 0.4.1 released

Removed the non-functional `agent run --async` flag and the hidden
keyword-based demo tool routing, so prompts now go straight to the runtime
model. Corrected docs that implied a shipped `miminions workflow` command.
Tagged `v0.4.1`.

Theme: removing placeholder surfaces that misrepresented capability.

## 2026-08-25 — 0.4.0 released

The reliability and observability release. Streaming replies, retries with
backoff, request timeouts, observability callbacks, message-history trimming,
workspace schema versioning, atomic JSON persistence, centralized path
resolution with `MIMINIONS_HOME`. Tagged `v0.4.0`.
See `reference/2026-08-24-release-0.4.0-prep.md`.

## 2026-07-02 — 0.3.0 released

Click-based CLI with nine command groups reached its shipped shape. Tagged
`v0.3.0`.

## 2026-07-13 — CLI hardening pass

Concentrated work on CLI ergonomics and correctness, recorded across seven
reference files on a single day: `agent show`, `config get/set`, `export/import`,
`init`, a shared `--json` flag, shared JSON I/O helpers, optional SQLite
dependencies, and cross-reference validation.

The density of records here makes this the best-documented period in the
project's history.

## 2026-04-02 — 0.2.2 released

Earliest tagged release. Development dependency handling settled, including the
`sqlite` extra for local development. Tagged `v0.2.2`.

## 2026-01 to 2026-06 — Principal build-out

The heaviest sustained activity in the project's life, roughly 250 commits.
Most current subpackages took shape in this window. CI arrived partway through
with `python-app.yml` and `python-publish.yml`.

## 2025-06 to 2025-12 — Reboot as an agentic framework

Steady, moderate activity re-establishing the project around pydantic-ai, MCP
support, and vector memory. This is where the current architecture originates.

## 2025-03 — Reactivation

Work resumes after a roughly twenty-month dormancy.

## 2023-05 — Origin

First commits, described in the initial commit message as "a miniature openai
chatgpt system." Approximately twenty commits over two days, then dormant. The
current codebase shares essentially nothing with this phase beyond the name.
