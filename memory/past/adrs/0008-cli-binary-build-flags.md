# 0008. PyInstaller binary requires explicit collection flags

Date: 2026-09-01
Status: accepted

## Context

`deploy/build_cli.sh` built the standalone binary with only
`--onefile --paths src`. On 2026-09-01, when the binary was first exercised
beyond building, it turned out to be **non-functional**: it crashed on launch,
and after that was fixed, every command group failed with
`ModuleNotFoundError`. Only `--version` and `--help` had ever worked.

Nothing in CI ran the binary, and building it succeeds regardless, so the
failure was invisible.

Three independent causes, each needing a different flag:

1. **Lazy command loading.** `cli/main.py` resolves command groups through
   `importlib.import_module` at invocation time (added by the CLI help lazy-load
   work). PyInstaller's static analysis cannot follow that, so no command module
   was bundled.
2. **logfire source introspection.** `logfire` arrives transitively through
   `pydantic-ai` and patches pydantic via `inspect.getsource`. A frozen bundle
   has no source to read, so importing anything pydantic-based raised
   `OSError: could not get source code`. MiMinions does not use logfire.
3. **Runtime metadata reads.** `miminions`, `pydantic-ai-slim`, and
   `genai_prices` read their own installed version via
   `importlib.metadata`, which needs the `.dist-info` copied into the bundle.

## Decision

Express the build in a committed `miminions-cli.spec` at the repository root,
used by both `deploy/build_cli.sh` and the `cli-binary` CI job. The spec carries
three things that PyInstaller cannot infer:

```python
hiddenimports = collect_submodules("miminions")   # defeats importlib lazy loading
excludes = ["logfire"]                            # NOT logfire_api, which is required
datas = copy_metadata("miminions")                # plus pydantic-ai-slim, genai_prices
```

Build the binary once per OS in `python-publish.yml` and attach all three to the
GitHub release, since a PyInstaller executable cannot be cross-built.

Install with the `all` extra before building. This is not optional: a user who
downloads a standalone binary has no way to `pip install miminions[sqlite]`
later, so anything left out is unreachable forever.

`*.spec` is gitignored by the standard Python template; `.gitignore` carries an
explicit `!miminions-cli.spec` negation because this one is curated, not
generated.

## Consequences

- The binary actually works. All nine command groups verified.
- **`--exclude-module logfire_api` would break the build.** `pydantic_graph`
  imports it directly. Only the full `logfire` package is excluded. These two
  names are one character apart and the failure is a confusing
  `ModuleNotFoundError` deep inside pydantic; hence this note.
- One source of truth. Adding a build setting means editing the spec, and both
  callers pick it up.
- **`--help` is not a sufficient smoke test.** Because command groups load
  lazily, `--help` passes while every actual command is missing. CI therefore
  invokes `<group> --help` for all nine groups.
- Binary size is roughly 108 MB, dominated by `onnxruntime` from the `sqlite`
  extra. A build without the `all` extra comes out around 95 MB and looks fine
  until vector memory is used, so size is a useful sanity signal.
- Adding a dependency that reads its own metadata at runtime means adding
  another `copy_metadata` entry. The symptom is `PackageNotFoundError` at
  startup.
