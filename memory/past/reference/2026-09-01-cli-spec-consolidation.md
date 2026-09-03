# CLI Binary Spec File Consolidation

Date: 2026-09-01

Resolves OQ-9. Amends `2026-09-01-cli-binary-and-release-matrix.md`.

## External Sources

- None. Local repository files and local builds.

## Direct References

- `deploy/build_cli.sh`: build entry point.
- `.github/workflows/python-publish.yml`: `cli-binary` job.
- `.gitignore`: the `*.spec` rule from the standard Python template.
- `memory/past/adrs/0008-cli-binary-build-flags.md`.

## Decisions

- **OQ-9, option 1.** Committed `miminions-cli.spec` at the repository root as
  the single source of build settings. Both callers reduce to
  `pyinstaller --clean miminions-cli.spec`.
- Used PyInstaller's `collect_submodules` and `copy_metadata` helpers in the
  spec rather than transcribing flag equivalents, so the spec expresses intent
  instead of restating CLI syntax.
- Added `!miminions-cli.spec` to `.gitignore` rather than removing the `*.spec`
  rule, since other spec files genuinely are build residue.
- Made the build install the `all` extra. Previously it installed only
  `cli-build`, which is a defect rather than a preference; see below.
- Kept `deploy/build_cli.sh` as the local entry point rather than having CI call
  it, avoiding a bash/`uv` dependency on the Windows runner.

## Findings

**The binary's contents depended on ambient environment state.** Both callers
installed only the `cli-build` extra, which prunes `sqlite`. The binary
therefore shipped without `fastembed`, `sqlite-vec`, or `onnxruntime` and had no
vector memory. This went unnoticed earlier today because the local environment
happened to have every extra synced from prior work, producing a ~110 MB binary;
a clean build produced ~95 MB.

This is worse than an ordinary missing dependency. A user who downloads a
standalone binary cannot run `pip install miminions[sqlite]` to recover, so
anything omitted at build time is unreachable permanently. Both callers now
install `all`.

**Verification method mattered.** `strings dist/miminions-cli | grep onnxruntime`
returned 0 even for a build that did contain it, because the bundle is
compressed. The reliable check is PyInstaller's own manifest:
`grep -c "fastembed\|onnxruntime" build/miminions-cli/Analysis-00.toc`, which
reported 136 entries. Recorded because the misleading check nearly produced a
wrong conclusion in both directions.

**The stale spec was live.** The untracked `miminions-cli.spec` at the root
referenced `main.py`, deleted some time ago, and was being silently regenerated
by each CLI-flag build. Replacing it with a curated file removes that trap.

## Generated Parts

- `miminions-cli.spec`, curated and committed.
- `deploy/build_cli.sh` reduced to sync plus spec invocation, with a `cd` to the
  repository root so it works from any directory.
- `cli-binary` job simplified to one build line; install changed to
  `.[all,cli-build]`.
- `.gitignore` negation.
- ADR 0008 amended: decision restated around the spec, consequences updated with
  the extras requirement and the size signal.
- OQ-9 closed.

## Validation

- `./deploy/build_cli.sh` from a clean `dist/` and `build/`: single-file
  artifact at 108 MB.
- All nine command groups plus `--version` and `--help` exited 0.
- `Analysis-00.toc` confirms 136 `fastembed`/`onnxruntime` entries bundled.
- Workflow YAML parses; `cli-binary` steps confirmed in order.
- `git check-ignore` confirms `miminions-cli.spec` is now trackable.
- macOS only. Linux and Windows remain unverified until a release runs.
