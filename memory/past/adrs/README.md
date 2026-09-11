# Architecture Decision Records

One decision per file, named `NNNN-title.md`. Append-only: an accepted ADR is
never edited except to add a `Superseded by:` line. To change a decision, write
a new ADR with a `Supersedes:` header.

## Format

```markdown
# NNNN. Title

Date: YYYY-MM-DD
Status: accepted | superseded | reconstructed

## Context
What forced a choice.

## Decision
What was chosen.

## Consequences
What this costs and constrains, including the bad parts.
```

## Status values

- **accepted** — decided contemporaneously and still in force.
- **reconstructed** — inferred after the fact from code and git history. The
  reasoning is plausible but was not recorded at the time. Treat the *decision*
  as fact and the *context* as inference.
- **superseded** — replaced. Must carry `Superseded by: NNNN`.

## Index

| ADR | Title | Status |
| --- | --- | --- |
| 0001 | pydantic-ai as the agent foundation | reconstructed |
| 0002 | fastembed over sentence-transformers | reconstructed |
| 0003 | pyproject-only packaging with ruff | reconstructed |
| 0004 | Optional heavy dependencies behind extras | reconstructed |
| 0005 | Narrow blocking lint gate over broad advisory one | reconstructed |
| 0006 | Authentication as an inert placeholder | reconstructed |
| 0007 | Local-first file state under MIMINIONS_HOME | reconstructed |
| 0008 | PyInstaller binary requires explicit collection flags | accepted |

ADRs 0001-0007 were reconstructed on 2026-09-01. 0008 was written the same day
but contemporaneously with the change it records.
