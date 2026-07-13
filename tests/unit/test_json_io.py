"""Tests for shared JSON IO helpers."""

import pytest

from miminions.utils.json_io import load_json, save_json


def test_load_json_returns_default_for_missing_file(tmp_path):
    path = tmp_path / "missing.json"

    assert load_json(path) == {}
    assert load_json(path, {"a": 1}) == {"a": 1}


def test_load_json_raises_value_error_for_invalid_json(tmp_path):
    path = tmp_path / "broken.json"
    path.write_text("{not valid", encoding="utf-8")

    with pytest.raises(ValueError):
        load_json(path)


def test_save_json_writes_atomically_and_load_round_trip(tmp_path):
    path = tmp_path / "config.json"
    payload = {"default_workspace": "ws_123"}

    save_json(path, payload, ensure_parent=True)
    assert load_json(path) == payload


def test_save_json_non_atomic_mode(tmp_path):
    path = tmp_path / "config.json"
    payload = {"default_agent": "default"}

    save_json(path, payload, ensure_parent=True, atomic=False)
    assert load_json(path) == payload
