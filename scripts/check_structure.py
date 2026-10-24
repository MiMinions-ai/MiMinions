#!/usr/bin/env python3
"""Gated structural check: tracked tree, STRUCTURE.md, MkDocs nav, module
contracts, and CLI groups must agree.

Implements the gate from docs/architecture/recursive-evolution.md.
Stdlib only; never imports the miminions package. Ignores __pycache__ and
*.pyc, so untracked local residue (e.g. a stale interface/ cache) is inert.

Usage: python scripts/check_structure.py [--root PATH]
Exit 0 = all checks pass; exit 1 = drift found (each failure printed).
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

CONTRACT_MARKER = "Recursive, Bounded Evolution"


def find_packages(src_root: Path) -> list[str]:
    """Package dirs under src/miminions holding at least one .py source."""
    packages = []
    for child in sorted(src_root.iterdir()):
        if not child.is_dir() or child.name == "__pycache__":
            continue
        if any(p.suffix == ".py" for p in child.rglob("*.py")):
            packages.append(child.name)
    return packages


def nav_doc_refs(mkdocs_text: str) -> list[str]:
    """All docs-relative .md paths referenced by mkdocs.yml."""
    return sorted(set(re.findall(r"[\w\-./]+\.md", mkdocs_text)))


def declared_exports(init_text: str) -> list[str]:
    """Every name in any __all__ list in an __init__.py (AST, no import)."""
    names: list[str] = []
    for node in ast.walk(ast.parse(init_text)):
        if isinstance(node, ast.Assign) and any(
            isinstance(target, ast.Name) and target.id == "__all__" for target in node.targets
        ) and isinstance(node.value, (ast.List, ast.Tuple)):
            names.extend(
                element.value
                for element in node.value.elts
                if isinstance(element, ast.Constant) and isinstance(element.value, str)
            )
    return names


def cli_entry_points(cli_main_text: str) -> list[str]:
    """Lazy groups plus standalone add_command registrations (e.g. init)."""
    lazy = re.findall(r'\(\s*"([a-z]+)"\s*,\s*"miminions\.cli\.', cli_main_text)
    standalone = re.findall(r'add_command\(\w+,\s*name="([a-z]+)"', cli_main_text)
    return sorted(set(lazy) | set(standalone))


def lazy_cli_commands(cli_main_text: str) -> list[str]:
    """Command names from the _LAZY_COMMANDS table in cli/main.py."""
    return re.findall(r'\(\s*"([a-z]+)"\s*,\s*"miminions\.cli\.', cli_main_text)


def run_checks(root: Path) -> list[str]:
    failures: list[str] = []
    src_root = root / "src" / "miminions"
    structure_path = root / "STRUCTURE.md"
    spec_path = root / "docs" / "architecture" / "recursive-evolution.md"
    if not src_root.is_dir() or not structure_path.is_file():
        return [f"repo layout not found under {root}"]

    structure = structure_path.read_text(encoding="utf-8")
    spec = spec_path.read_text(encoding="utf-8") if spec_path.is_file() else ""
    if not spec:
        failures.append("missing spec: docs/architecture/recursive-evolution.md")

    packages = find_packages(src_root)
    for name in packages:
        pkg = src_root / name
        readme = pkg / "README.md"
        init_path = pkg / "__init__.py"
        if init_path.is_file() and readme.is_file():
            readme_text = readme.read_text(encoding="utf-8")
            for export in declared_exports(init_path.read_text(encoding="utf-8")):
                if export not in readme_text:
                    failures.append(f"{name}: export '{export}' in __all__ but not documented in README.md")
        if not (pkg / "__init__.py").is_file():
            failures.append(f"{name}: missing __init__.py")
        if not readme.is_file():
            failures.append(f"{name}: missing README.md (five-block contract home)")
        elif CONTRACT_MARKER not in readme.read_text(encoding="utf-8"):
            failures.append(f"{name}: README.md lacks contract marker '{CONTRACT_MARKER}'")
        if f"{name}/" not in structure:
            failures.append(f"{name}: not mentioned in STRUCTURE.md")
        if f"`{name}`" not in spec:
            failures.append(f"{name}: not in spec contract registry")

    mkdocs_text = (root / "mkdocs.yml").read_text(encoding="utf-8")
    for ref in nav_doc_refs(mkdocs_text):
        if not (root / "docs" / ref).is_file():
            failures.append(f"mkdocs nav: docs/{ref} does not exist")

    cli_main = (src_root / "cli" / "main.py").read_text(encoding="utf-8")
    for cmd in cli_entry_points(cli_main):
        if cmd not in structure:
            failures.append(f"cli group '{cmd}': registered in cli/main.py but absent from STRUCTURE.md")

    if (root / "memory").is_dir():
        failures.append("memory/: internal docs belong in the private docs-internal repo, not the public tree")
    if (root / "docs" / "test-quality-control.md").is_file():
        failures.append("docs/test-quality-control.md: internal docs belong in the private docs-internal repo (quality/)")

    return failures


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).resolve().parent.parent)
    args = parser.parse_args(argv)
    failures = run_checks(args.root.resolve())
    if failures:
        print(f"FAIL ({len(failures)}):")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    print("PASS: tree, STRUCTURE.md, MkDocs nav, contracts, surfaces, and CLI entry points agree.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
