"""Tests for the shared CLI JSON persistence helpers."""

import pytest

from miminions.cli.persistence import load_json, save_json


def test_load_missing_file_returns_empty(tmp_path):
    assert load_json(tmp_path / "nope.json") == {}


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "store.json"
    data = {"a": 1, "nested": {"b": [1, 2, 3]}}

    save_json(path, data)

    assert path.exists()
    assert load_json(path) == data


def test_save_is_atomic_no_tmp_left_behind(tmp_path):
    path = tmp_path / "store.json"
    save_json(path, {"x": 1})

    # The temp file used for the atomic replace must not survive.
    assert not (tmp_path / "store.tmp").exists()


def test_save_creates_parent_dirs(tmp_path):
    path = tmp_path / "deep" / "nested" / "store.json"
    save_json(path, {"ok": True})
    assert load_json(path) == {"ok": True}


def test_load_corrupt_json_raises_value_error(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{ not valid json")

    with pytest.raises(ValueError):
        load_json(path)
