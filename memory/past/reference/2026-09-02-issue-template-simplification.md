# Issue Template Simplification

Date: 2026-09-02

## External Sources

- None. Local repository files and user direction.

## Direct References

- `.github/ISSUE_TEMPLATE/config.yml`, `bug_report.yml`, `feature_request.yml`,
  `question.yml`: last touched 2025-08-09.
- `CODE_OF_CONDUCT.md`: real link target.
- `pyproject.toml`: `requires-python = ">=3.12"`.

## Decisions

- Set `blank_issues_enabled: true` per user direction, so contributors can open
  an unstructured issue.
- Cut required fields to what triage actually needs: bug 10 fields -> 4,
  feature 10 -> 3, question 8 -> 1. Net 254 deletions against 34 insertions.
- Merged overlapping fields rather than deleting information wholesale.
  "Expected Behavior" and "Actual Behavior" were separate required textareas
  restating "What happened?"; version, OS, and Python version became a single
  `Environment` line.
- Dropped `assignees: octocat` and `projects: ["MiMinions-ai/1"]`.
- Dropped the "Priority Level" and "Feature Category" dropdowns. Self-reported
  priority is not evidence, and the category list named subsystems that do not
  map to the current module layout.
- Removed the duplicate "Community Chat" contact link, which pointed at the same
  Discussions URL as the entry above it.
- Kept the Code of Conduct checkbox on all three, with a working link.

## Findings

Four defects, all shipped and all invisible without reading the files:

- **`assignees: octocat`** on `bug_report.yml` and `feature_request.yml`. GitHub
  template scaffolding placeholder; would attempt to assign a non-collaborator.
- **Code of Conduct linked to `https://example.com`** in all three templates,
  behind a required checkbox. Contributors were agreeing to a placeholder.
- **Python version dropdown offered 3.8 through 3.12**, defaulting to 3.8, while
  `pyproject.toml` requires `>=3.12`. Reporters were invited to select
  unsupported versions.
- **Duplicate contact link**: "Community Chat" and "Discussions" both pointed at
  `/discussions`.

## Generated Parts

- `config.yml`: blank issues enabled, duplicate link removed.
- `bug_report.yml`: what happened, steps, error output, environment, CoC.
- `feature_request.yml`: problem, proposal, contribution, CoC.
- `question.yml`: question, CoC, plus a pointer to Discussions.

## Needs user confirmation

`projects: ["MiMinions-ai/1"]` was removed from all three templates. It
auto-added new issues to a project board. If that board is in use, the line
should be restored; it was dropped alongside the `octocat` placeholder as
scaffolding, which may be wrong.

## Validation

- All four files parse as YAML.
- Every non-markdown block has a unique `id`; all `type` values are valid GitHub
  issue-form types.
- No remaining references to `octocat`, `example.com`, or `projects:`.
- Rendering is not verifiable locally; GitHub validates issue forms server-side
  on push.
