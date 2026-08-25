"""Tests for shared JSON IO helpers."""

import pytest

from miminions.utils.json_io import load_json, save_json


def test_load_json_returns_default_for_missing_file(tmp_path):
    path = tmp_path / "missing.json"

    result = load_json(path)
    assert result == {}, f"expect the result of load_json(path) without default to be {{}}, got {result}"

    result = load_json(path, default={"a": 1})
    assert result == {"a": 1}, f"expect the result of load_json(path, default={{'a': 1}}) to be {{'a': 1}}, got {result}"



def test_load_json_raises_value_error_for_invalid_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not valid", encoding="utf-8")

    with pytest.raises(ValueError):
        load_json(path)


def test_save_json_writes_atomically_and_load_round_trip(tmp_path):
    path = tmp_path / "config.json"
    payload = {"default_workspace": "ws_123"}

    save_json(path, payload, ensure_parent=True)
    result = load_json(path)
    assert result == payload, f"expect the result of load_json(path) to be {payload}, got {result}"


def test_save_json_non_atomic_mode(tmp_path):
    path = tmp_path / "config.json"
    payload = {"default_agent": "default"}

    save_json(path, payload, ensure_parent=True, atomic=False)
    result = load_json(path)
    assert result == payload, f"expect the result of load_json(path) to be {payload}, got {result}"
