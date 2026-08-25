"""Tests for the shared CLI JSON persistence helpers."""

import pytest

from miminions.cli.persistence import load_json, save_json


def test_load_missing_file_returns_empty(tmp_path):
    assert load_json(tmp_path / "nope.json") == {}, f"expect result to be {{}}, got {load_json(tmp_path / 'nope.json')}"


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "store.json"
    data = {"a": 1, "nested": {"b": [1, 2, 3]}}

    save_json(path, data)

    path_exists = path.exists()
    assert path_exists, f"expect save_json writes target file to disk, got {path_exists}"
    assert load_json(path) == data, f"expect result to be {data}, got {load_json(path)}"


def test_save_is_atomic_no_tmp_left_behind(tmp_path):
    path = tmp_path / "store.json"
    save_json(path, {"x": 1})

    # The temp file used for the atomic replace must not survive.
    temp_file_exists = (tmp_path / "store.tmp").exists()
    assert not temp_file_exists, f"expect save_json atomic replace leaves no store.tmp file, got {temp_file_exists}"


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "store.json"
    save_json(path, {"ok": True})
    assert load_json(path) == {"ok": True}, f"expect result to be {{'ok': True}}, got {load_json(path)}"


def test_load_corrupt_json_raises_value_error(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ not valid json")

    with pytest.raises(ValueError):
        load_json(path)
