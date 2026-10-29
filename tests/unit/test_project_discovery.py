"""Import-free scanning, filtering, metadata, and incremental cache behavior."""

import json
from pathlib import Path

import pytest

from miminions.workspace_fs import discovery


def write(root, relative, source):
    path = root / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(source, encoding="utf-8")
    return path


def test_discovery_never_executes_project_expressions(tmp_path):
    write(tmp_path, "main.py", '''
raise AssertionError("must not import")
from third_party import imported
from typing import Optional as Maybe
def report(rows: list[dict[str, int]], title: Maybe[str] = None, *, count: int = 3) -> str:
    """Generate a CSV report."""
    return title
async def fetch(url: "str"):
    return url
def dangerous_default(path=side_effect()): pass
def dangerous_type(x: side_effect()): pass
''')
    context = discovery.scan_project(tmp_path)
    assert [f.name for f in context.functions] == ["report", "fetch"]
    function = context.functions[0]
    assert function.docstring == "Generate a CSV report."
    assert function.return_annotation == "str"
    assert function.parameters[0]["type"] == {"kind": "list", "items": {"kind": "dict", "items": {"kind": "int"}}}
    assert function.parameters[1]["type"]["kind"] == "union"
    assert function.parameters[2]["default"] == 3
    assert function.parameters[2]["keyword_only"]
    assert "rows:" in function.signature and function.line > 0
    assert context.functions[1].is_async
    assert len(context.warnings) == 2


def test_filters_ineligible_definitions_without_confusing_inner_scopes(tmp_path):
    write(tmp_path, "functions.py", '''
from other import imported
def _private(): pass
@decorator
def decorated(): pass
def variadic(*args): pass
def positional(x, /): pass
def generator(): yield 1
def overwritten(): pass
overwritten = 1
def overwritten_by_import(): pass
from other import overwritten_by_import
def kept(value: int):
    def nested(): yield 1
    return value
def another():
    kept = 2
    return kept
class Example:
    def method(self): pass
if True:
    def conditional(): pass
''')
    write(tmp_path, "tests/helpers.py", "def helper(): pass")
    write(tmp_path, "test_report.py", "def report(): pass")
    context = discovery.scan_project(tmp_path)
    assert [f.name for f in context.functions] == ["kept", "another"]
    assert len(context.warnings) == 6


def test_nested_ignore_rules_and_permanent_exclusions(tmp_path, monkeypatch):
    write(tmp_path, ".gitignore", "ignored/\n*.py\n!keep.py\n!nested/\n")
    write(tmp_path, "nested/.gitignore", "!useful.py\n")
    for relative in ("ignored/keep.py", "keep.py", "skip.py", "nested/useful.py", "nested/skip.py",
                     ".git/keep.py", ".venv/keep.py", "node_modules/keep.py", "build/keep.py"):
        write(tmp_path, relative, "def useful(): return 'ok'")
    state = tmp_path / "custom-state"
    monkeypatch.setenv("MIMINIONS_HOME", str(state))
    write(state, "keep.py", "def should_ignore(): pass")
    context = discovery.scan_project(tmp_path)
    assert [f.path for f in context.functions] == ["keep.py", "nested/useful.py"]


def test_symlinks_are_excluded(tmp_path):
    outside = tmp_path / "outside"
    outside.mkdir()
    source = write(outside, "source.py", "def outside_function(): pass")
    project = tmp_path / "project"
    project.mkdir()
    try:
        (project / "linked.py").symlink_to(source)
        (project / "linked_dir").symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("Symlinks unavailable for this Windows account")
    assert discovery.scan_project(project).functions == []


def test_cache_updates_deletes_and_recovers_corruption(tmp_path, monkeypatch):
    project = tmp_path / "project"
    source = write(project, "main.py", "def first(x: int): return x")
    cache = tmp_path / "state/discovery.json"
    first = discovery.scan_project(project, cache)
    original = discovery._parse_file
    monkeypatch.setattr(discovery, "_parse_file", lambda *args: pytest.fail("Unchanged source should use cache"))
    assert discovery.scan_project(project, cache).functions == first.functions
    monkeypatch.setattr(discovery, "_parse_file", original)
    source.write_text("def changed(x: int): return x + 1", encoding="utf-8")
    changed = discovery.scan_project(project, cache)
    assert changed.functions[0].name == "changed"
    assert changed.functions[0].digest != first.functions[0].digest
    write(project, ".gitignore", "main.py\n")
    assert not discovery.scan_project(project, cache).functions
    (project / ".gitignore").unlink()
    for content in ("{corrupt", json.dumps({"version": discovery.SCANNER_VERSION, "root": str(project), "files": []})):
        cache.write_text(content, encoding="utf-8")
        assert discovery.scan_project(project, cache).functions[0].name == "changed"
    source.unlink()
    assert not discovery.scan_project(project, cache).functions
    assert json.loads(cache.read_text())["files"] == {}


def test_limits_encoding_and_read_failures_are_reported(tmp_path, monkeypatch):
    write(tmp_path, "bad.py", "def not_valid(:")
    write(tmp_path, "huge.py", "#" * (discovery.MAX_FILE_BYTES + 1))
    write(tmp_path, "README.md", "Project purpose")
    encoded = tmp_path / "encoded.py"
    encoded.write_bytes(b"# coding: latin-1\ndef cafe():\n    '''caf\xe9'''\n")
    denied = write(tmp_path, "denied.py", "def denied(): pass")
    original = discovery.source_bytes
    def read(root, relative):
        if relative == denied.name:
            raise PermissionError("denied")
        return original(root, relative)
    monkeypatch.setattr(discovery, "source_bytes", read)
    context = discovery.scan_project(tmp_path)
    assert [f.name for f in context.functions] == ["cafe"]
    assert context.functions[0].docstring == "café"
    assert len(context.warnings) == 3
    assert context.excerpts["README.md"] == "Project purpose"
    assert any("truncated" in w for w in discovery.scan_project(tmp_path, max_entries=1).warnings)


@pytest.mark.parametrize("annotation", ["int | str | None", "str | None", "typing.Optional[list[int]]", "'dict[str, bool]'"])
def test_safe_supported_annotations(tmp_path, annotation):
    write(tmp_path, "main.py", f"import typing\ndef run(value: {annotation}): pass")
    assert len(discovery.scan_project(tmp_path).functions) == 1


def test_tool_names_are_stable_unique_and_provider_safe(tmp_path):
    for relative in ("one/main.py", "two/main.py"):
        write(tmp_path, relative, "def shared(x: int = 1): return x")
    first = discovery.scan_project(tmp_path)
    second = discovery.scan_project(tmp_path)
    assert [f.tool_name for f in first.functions] == [f.tool_name for f in second.functions]
    assert len({f.tool_name for f in first.functions}) == 2
    assert all(len(f.tool_name) <= 64 and f.tool_name.isascii() for f in first.functions)


def test_project_detection_and_context_budget(tmp_path):
    assert not discovery.detect_project(tmp_path)
    write(tmp_path, ".venv/hidden.py", "def hidden(): pass")
    assert not discovery.detect_project(tmp_path)
    write(tmp_path, "pyproject.toml", "[project]\nname='demo'")
    assert discovery.detect_project(tmp_path)
    write(tmp_path, "README.md", "PURPOSE " * 2000)
    context = discovery.scan_project(tmp_path)
    from miminions.memory.budget import count_tokens
    assert count_tokens(context.prompt()) <= 4000
    assert "untrusted reference data" in context.prompt()


def test_invalid_encoding_and_corrupt_metadata_cache_recover(tmp_path):
    project = tmp_path / "project"
    write(project, "bad.py", "# coding: nonexistent-encoding\ndef bad(): pass")
    write(project, "good.py", "def good(value: int): return value")
    cache = tmp_path / "state/discovery.json"
    context = discovery.scan_project(project, cache)
    assert [f.name for f in context.functions] == ["good"]
    assert len(context.warnings) == 1
    data = json.loads(cache.read_text())
    data["files"]["good.py"]["functions"][0]["parameters"] = [{"invalid": True}]
    cache.write_text(json.dumps(data), encoding="utf-8")
    context = discovery.scan_project(project, cache)
    assert context.functions[0].parameters[0]["name"] == "value"


def test_junction_like_directories_are_skipped(tmp_path, monkeypatch):
    write(tmp_path, "linked/hidden.py", "def hidden(): pass")
    write(tmp_path, "visible.py", "def visible(): pass")
    original = discovery.is_link
    monkeypatch.setattr(discovery, "is_link", lambda path: path.name == "linked" or original(path))
    assert [f.name for f in discovery.scan_project(tmp_path).functions] == ["visible"]
