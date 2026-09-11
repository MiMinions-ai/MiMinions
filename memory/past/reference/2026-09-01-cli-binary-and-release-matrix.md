# CLI Binary Repair, Release Matrix, External Tier

Date: 2026-09-01

## External Sources

- None. Local repository files, local builds, and user direction.

## Direct References

- `.github/workflows/python-app.yml`: CI triggers.
- `.github/workflows/python-publish.yml`: release workflow.
- `deploy/build_cli.sh`: PyInstaller invocation.
- `src/miminions/cli/main.py`: lazy command-group loading via `importlib`.
- `pyproject.toml`, `uv tree`: dependency facts for the external landscape.

## Decisions

- **OQ-7, option 2.** Added `development` to `pull_request` branches only. Push
  runs stay limited to `main`, so merges into the integration branch are gated
  without doubling CI on direct pushes.
- **OQ-8, option 1.** Added a `cli-binary` job building the PyInstaller
  executable on ubuntu/macOS/Windows, plus `attach-binaries` uploading all three
  to the GitHub release with platform-suffixed names.
- Left the binary jobs off the `publish` dependency chain. A binary build
  failure should not block the PyPI wheel, which is the primary artifact.
- Kept the PyInstaller flags duplicated between script and workflow rather than
  introducing a committed spec file, since CI now smoke-tests all nine command
  groups on all three platforms and would catch drift. Filed as OQ-9.
- Scoped `past/external/` to upstreams, alternatives, and adjacent projects per
  user direction, with an explicit rule that unverified claims may not be
  recorded as fact.

## Findings

**The standalone CLI binary has never worked.** It built successfully, which is
why nothing caught it, but it failed at runtime in three independent ways:

1. Launch crashed with `OSError: could not get source code`. `logfire`, pulled
   in transitively by `pydantic-ai`, patches pydantic through
   `inspect.getsource`, and a frozen bundle has no source. MiMinions never uses
   logfire.
2. After excluding it, every command group failed with `ModuleNotFoundError`.
   `cli/main.py` resolves groups through `importlib.import_module`, which
   PyInstaller's static analysis cannot follow, so no command module was
   bundled. Fixed with `--collect-submodules miminions`.
3. Then `PackageNotFoundError` for `genai_prices`. Several packages read their
   own version through `importlib.metadata`, needing `--copy-metadata`.

A near-miss worth recording: excluding `logfire_api` alongside `logfire` breaks
the build, because `pydantic_graph` imports it directly. The two names differ by
one suffix and require opposite treatment.

**`--help` is not a sufficient smoke test** for this CLI. Because groups load
lazily, `--help` passed while every real command was missing. CI now invokes
`<group> --help` for all nine groups.

**A test-harness bug of my own**, worth noting because it nearly produced a
false conclusion: a zsh loop of the form `for c in "agent --help"; do binary $c`
does not word-split, so the binary received one argument and reported failure
for commands that actually worked. zsh requires `${=c}`. Two "failures" were
mine, not the binary's.

## Generated Parts

- `development` added to `pull_request` branches in `python-app.yml`.
- `cli-binary` and `attach-binaries` jobs in `python-publish.yml`.
- `deploy/build_cli.sh` rewritten with the five required flags and comments.
- `memory/past/adrs/0008-cli-binary-build-flags.md`.
- `memory/past/external/README.md` and `landscape.md`.
- `open-questions.md` rewritten: OQ-7 and OQ-8 closed, OQ-4 refocused on
  populating adjacent projects, OQ-9 added.
- `conventions.md`, `state.md`, ADR index, and `INDEX.md` updated.

## Validation

- `deploy/build_cli.sh` run end to end: binary built and all nine command groups
  plus `--version` and `--help` exited 0. Size ~110 MB.
- Workflow YAML parses; job graph confirmed as `build -> verify -> publish` and
  `cli-binary(3 OS) -> attach-binaries`.
- `uv run pytest -q`: 622 passed.
- `uv run ruff check .`: clean.
- macOS is the only platform verified locally. Linux and Windows binaries are
  built by CI and unverified until the next release runs.
