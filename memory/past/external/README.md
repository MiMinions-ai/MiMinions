# External Landscape

Open-source projects in close proximity to MiMinions: what we build on, what we
could adopt instead, and what we are measured against.

This tier exists so that dependency and positioning decisions are made against a
recorded picture rather than from memory. It is part of `past/` because entries
are **dated observations**, not live status. An entry states what was true when
it was written; it does not update itself.

## Scope

Include a project if at least one is true:

- **Upstream** — MiMinions depends on it, so its direction constrains ours.
- **Alternative** — it could replace something we depend on. Records what we
  chose against, which is the part that is otherwise lost.
- **Adjacent** — it solves an overlapping problem for the same users, so it
  shapes what MiMinions is compared to.

Exclude transitive dependencies unless they have bitten us. `logfire` earns an
entry for exactly that reason (ADR 0008); `numpy` does not.

## File layout

One file per project: `<project-slug>.md`. `landscape.md` holds the index and
the relationship summary.

## Entry format

```markdown
# project-name

Relationship: upstream | alternative | adjacent
Observed: YYYY-MM-DD
Source: <url>

## What it is
One or two sentences.

## Why it matters to MiMinions
The concrete coupling or overlap. Name the ADR if one exists.

## Risks and constraints
Version pins, breaking-change history, licence, maintenance signals.

## Notes
Anything dated and specific.
```

## Rules

1. **Never record a claim that was not checked.** An unverified belief about
   another project is worse than no entry, because it reads as researched. Mark
   anything unconfirmed as `Unverified:` explicitly.
2. **Date every observation.** Upstream projects move; an undated claim about a
   moving target is unusable.
3. **Cite a source URL** for factual claims. If there is no source, say where the
   belief came from.
4. Entries are append-only like the rest of `past/`. Revising means adding a
   dated section, not editing an old one.
5. Keep judgement out of `## What it is` and confined to
   `## Why it matters to MiMinions`.
