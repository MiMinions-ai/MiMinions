"""Focused tests for the structural gate (scripts/check_structure.py)."""

import importlib.util
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT = REPO_ROOT / "scripts" / "check_structure.py"


def _load_gate():
    spec = importlib.util.spec_from_file_location("check_structure", SCRIPT)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_repo_satisfies_structure_gate():
    gate = _load_gate()
    assert gate.run_checks(REPO_ROOT) == []


def test_gate_flags_uncontracted_package(tmp_path):
    gate = _load_gate()
    pkg = tmp_path / "src" / "miminions" / "foo"
    pkg.mkdir(parents=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")
    (pkg / "mod.py").write_text("", encoding="utf-8")
    # cli/workflow files the gate always reads:
    cli = tmp_path / "src" / "miminions" / "cli"
    cli.mkdir(parents=True)
    (cli / "__init__.py").write_text("", encoding="utf-8")
    (cli / "main.py").write_text("", encoding="utf-8")
    wf = tmp_path / "src" / "miminions" / "workflow"
    wf.mkdir(parents=True)
    (wf / "__init__.py").write_text("", encoding="utf-8")
    (tmp_path / "STRUCTURE.md").write_text("# map\n", encoding="utf-8")
    (tmp_path / "mkdocs.yml").write_text("nav: []\n", encoding="utf-8")

    failures = gate.run_checks(tmp_path)
    assert any("foo" in failure and "README" in failure for failure in failures)

    # Internal docs must never reappear in the public tree:
    (tmp_path / "memory").mkdir()
    failures = gate.run_checks(tmp_path)
    assert any("docs-internal" in failure for failure in failures)

    # Undocumented exports must fail: give foo a contract README that
    # never mentions its declared export.
    (pkg / "README.md").write_text(
        "# foo\n\nRecursive, Bounded Evolution\n", encoding="utf-8"
    )
    (pkg / "__init__.py").write_text(
        '__all__ = ["NotDocumented"]\n', encoding="utf-8"
    )
    failures = gate.run_checks(tmp_path)
    assert any("NotDocumented" in failure for failure in failures)
