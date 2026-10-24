## Description

Brief description of what this PR does and why it's needed.

Fixes # (issue)

## What changed

Describe the main changes in this PR:

## Why the changes are needed

Describe the reasoning of the changes made

## How to validate the changes

Describe the method to validate the changes as intended.
Can be a cli command with changed behavior.

## Contract (gated — see docs/architecture/recursive-evolution.md)

- [ ] No module contract touched, or: contract updated in the same PR
      (module README Purpose / Public surface / State / Lifecycle / Gate).
- [ ] Public surface or on-disk state changed? Contract version bumped
      with a migration note. Otherwise: no version bump needed.
- [ ] `python scripts/check_structure.py` passes locally.

## Testing

Describe how you tested these changes:

## Additional Notes (optional)

Any other information reviewers should know.