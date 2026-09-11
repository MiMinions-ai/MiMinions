# Landscape Index

Observed: 2026-09-01

Entries below are seeded from **verified local facts only**: the dependency
graph in `pyproject.toml` and `uv tree`, plus incidents recorded in this
repository's ADRs. Nothing here was researched externally, so no claim is made
about any project's roadmap, popularity, or comparative merit.

Adjacent projects — the ones MiMinions is positioned against — are deliberately
left empty. See "Gaps" below.

## Upstream (verified from the dependency graph)

| Project | Pinned as | Resolved | Why it matters |
| --- | --- | --- | --- |
| pydantic-ai | `>=1.0.0,<2.0.0` | 1.107.0 | The agent runtime. ADR 0001. |
| mcp | `>=1.23.0` | 1.28.1 | Model Context Protocol tool servers. |
| click | `>=8.0.0` | 8.4.2 | Entire CLI surface. |
| openai | `>=2.14.0` | 2.44.0 | Provider SDK. |
| pydantic | `>=2.0.0` | 2.13.4 | Models throughout. |
| fastembed | `>=0.3.0` (extra) | 0.8.0 | Embeddings. ADR 0002, ADR 0004. |
| sqlite-vec | `>=0.1.0` (extra) | 0.1.9 | Vector search. ADR 0004. |
| pysqlite3 | `>=0.6.0` | 0.6.0 | Loadable-extension SQLite. ADR 0004. |
| pyinstaller | `>=6.0.0` (extra) | 6.21.0 | Standalone binary. ADR 0008. |

Two upstreams carry a **hard version ceiling or floor for recorded reasons**:

- `pydantic-ai` is capped below 2.0.0. A CI break on 2026-06-26 showed the API
  surface moves between minors, so the cap is load-bearing (ADR 0001).
- `ruff` is floored at `>=0.16.5` because rule behavior varies by version and an
  unpinned resolve had silently produced 0.15.20 (ADR 0005).

## Transitive, but consequential

| Project | Arrives via | Why it earns an entry |
| --- | --- | --- |
| logfire | pydantic-ai | Patches pydantic through `inspect.getsource`; broke the frozen CLI binary entirely. Excluded from PyInstaller builds. ADR 0008. |
| logfire-api | pydantic-graph | Required. Must **not** be excluded — one character from `logfire`, opposite treatment. ADR 0008. |
| onnxruntime | fastembed | Dominates the ~110 MB binary size and the `sqlite` extra install cost. |

## Alternatives we chose against

| Considered | Chosen | Recorded in |
| --- | --- | --- |
| sentence-transformers (PyTorch/CUDA) | fastembed (ONNX) | ADR 0002 |
| flake8 | ruff | ADR 0003 |
| setup.py + setup.cfg | pyproject-only | ADR 0003 |

## Gaps

**No adjacent projects are recorded.** MiMinions describes itself as an agentic
framework with MCP support and vector memory, which is a crowded space, but
naming competitors from memory would violate rule 1 in `README.md`.

Populating this needs a deliberate pass with sources. Useful axes when it
happens:

- Local-first CLI agents vs. hosted/server agent platforms (ADR 0007 commits us
  to the former, so the comparison set should respect that).
- Frameworks built on pydantic-ai specifically, since ADR 0001 makes their
  breakage our breakage.
- Vector-memory-over-SQLite tools, the closest analogue to `SQLiteMemory`.

Until then, the absence is recorded rather than papered over.
