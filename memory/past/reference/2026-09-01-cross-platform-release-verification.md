# Cross-Platform Release Verification

Date: 2026-09-01

## External Sources

- None. Local repository files and user direction.

## Direct References

- `.github/workflows/python-publish.yml`: release workflow.
- `deploy/build_cli.sh`: PyInstaller CLI binary build.
- `pyproject.toml`: `cli-build` extra, `all` extra.
- `dist/miminions-0.4.1-py3-none-any.whl`: built artifact.

## Request

Add a build step on `macos-latest` and Windows to the publish workflow.

## Decisions

Implemented as a **verification** matrix rather than a build matrix.

The wheel is `py3-none-any` — pure Python with no compiled extensions. Building
it on three operating systems produces three byte-identical artifacts with the
same filename, which would collide on upload to PyPI and add release time
without reducing risk.

What the request was actually protecting against — the package failing on macOS
or Windows — is real, because several dependencies (`pysqlite3`, `onnxruntime`
via `fastembed`) ship platform-specific compiled wheels. So the matrix was
applied to installation and smoke testing instead of to building.

Resulting job graph: `build` (ubuntu, one artifact) -> `verify`
(ubuntu/macOS/Windows, installs that artifact with `[all]` and smoke-tests it)
-> `publish` (ubuntu, trusted publishing). `publish` now depends on `verify`, so
a platform failure blocks the release.

Other choices:

- `fail-fast: false`, so one platform failing still reports the others. Knowing
  whether a break is Windows-only or universal is the useful signal.
- `shell: bash` on every scripted step, for one syntax across all three runners.
- Smoke test covers the console script (`--version`, `--help`) and a direct
  import of `miminions.memory.sqlite`, since that module is the one carrying
  platform-specific compiled dependencies.
- Installed with the `[all]` extra deliberately. A base-only install would not
  exercise `sqlite-vec`, `fastembed`, or `onnxruntime`, which is where
  cross-platform breakage would actually appear.

## Generated Parts

- `verify` job with a three-OS matrix in `python-publish.yml`.
- `publish` rewired from `needs: build` to `needs: verify`.
- Wheel-count assertion before install.
- `conventions.md` updated with the release job graph.
- OQ-8 added.

## Findings

- **The wheel glob is fragile.** A first attempt used
  `pip install "$(ls dist/*.whl)[all]"`, which broke locally because `dist/`
  held both a stale 0.4.0 wheel and the current 0.4.1 one, expanding to two
  paths. In CI `dist/` comes fresh from the build job so it would have passed,
  but silently installing an arbitrary wheel during a *release* is a bad failure
  mode. Replaced with an explicit assertion that exactly one wheel is present.
- **The PyInstaller binary is the real platform-specific artifact.**
  `deploy/build_cli.sh` produces a native executable that genuinely cannot be
  cross-built, and no CI job runs it. That is where a build matrix would be
  correct. Filed as OQ-8 rather than implemented, since it was not requested and
  depends on whether the binary is a supported channel.

## Validation

- Workflow YAML parses; job graph confirmed as
  `build -> verify(3 OS) -> publish`.
- Locally reproduced the verify steps against a clean 3.12 environment:
  wheel-count assertion passed, `pip install "<wheel>[all]"` succeeded,
  `miminions --version` reported 0.4.1, `miminions --help` exited 0, and
  `import miminions.agent, miminions.memory.sqlite` succeeded.
- Editor diagnostics clean on `python-publish.yml`.
- Note the local reproduction used zsh, where arrays are 1-indexed; the workflow
  pins `shell: bash`, where `${wheels[0]}` is the first element.
