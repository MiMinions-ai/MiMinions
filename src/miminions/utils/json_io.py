"""Shared JSON file IO helpers with safe defaults."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_json(path: Path, default: dict[str, Any] | None = None) -> dict[str, Any]:
    """Load JSON from path; return default (or {}) when the file is missing."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        if default is None:
            return {}
        return default.copy()
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def save_json(
    path: Path,
    data: dict[str, Any],
    *,
    ensure_parent: bool = False,
    atomic: bool = True,
) -> None:
    """Write JSON to path; atomic by default."""
    if ensure_parent:
        path.parent.mkdir(parents=True, exist_ok=True)

    if atomic:
        tmp = path.with_name(f"{path.name}.tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2)
        os.replace(tmp, path)
        return

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)