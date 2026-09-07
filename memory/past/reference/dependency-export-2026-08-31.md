# Dependency CSV Export

- Source: local `requirements.txt`, resolved by `uv pip install` for the active Python 3.12 interpreter on macOS.
- `dependency_relationships.csv` records active dependency edges, including dependencies selected through PEP 508 extras, `miminions` direct requirements, and its Python runtime edge.
- `package_stats.csv` records resolved version, installed on-disk size, PyPI releases per trailing 365 days, direct dependency count, direct dependent-package count, accumulated dependency count, maximum dependency depth, relative depth range, project group, package domain, and language. Release frequency counts distinct versions at their first PyPI upload; results are cached for seven days in `.analysis/dependencies/release-frequency-cache` and may be refreshed with `--refresh-release-frequencies`. Relative depth range is the exact shortest path and cycle-condensed longest path in edges from `miminions`, represented as `minimum-maximum`. Project group is parsed from the leading comments in `requirements.txt` and propagated to every reachable transitive dependency; multi-group memberships are separated by ` | `. Package domain is a transparent name-based classification, with `General utility` as the conservative fallback. Accumulated count includes unique direct and indirect dependencies; `miminions` also counts Python because it is an explicit runtime edge. Depth is the longest active dependency path, in edges, after treating each cyclic dependency group as one node.
- Language is recorded as `Python` for all rows because wheel metadata has no portable, authoritative language breakdown. Native extensions are included in the installed size but not separately classified.

## Schema update (2026-09-02)

- `pyproject.toml` is now the source for direct requirements and optional
  dependency scopes. `requirements.txt` is an editable-install pointer and no
  longer has the package-group comments this exporter previously parsed.
- `package_stats.csv` gained `package_key`, the PEP 503-normalized package name.
  It is the join key; `package` remains the display name from wheel metadata.
- `dependency_relationships.csv` is an edge table with normalized
  `parent_package_key` and `dependency_package_key`, plus
  `relationship_type` (`direct`, `transitive`, or `runtime`),
  `requirement_scope`, `requirement_specifier`, and `marker`.
- Direct project edges appear once per scope. For example, `fastembed` has both
  `sqlite` and `all` edges; that is intentional provenance, not duplication.
  Transitive edges have blank scope, specifier, and marker fields because they
  are resolved from installed wheel metadata rather than declared by MiMinions.
- The editable `miminions` distribution is excluded from resolved package nodes:
  it is represented exactly once as the graph root. This prevents it appearing
  as an unreachable package and breaking depth calculations.
- CSV writers use `lineterminator="\n"`, avoiding CRLF keys in shell or database
  consumers that do not use a CSV-aware parser.

Validation after regeneration: 189 nodes, 398 edges, and every relationship
endpoint joined to `package_stats.package_key`.
