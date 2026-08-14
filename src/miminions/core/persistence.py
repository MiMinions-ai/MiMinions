"""Shared JSON persistence helpers.

Most MiMinions state is a small JSON file under the config directory. These
helpers centralize reading and writing it with a UTF-8, atomic write so an
interrupted save can't leave a half-written (corrupt) file behind. Living in
``core`` keeps them importable from both ``core`` (e.g. bootstrap) and ``cli``
without a layering inversion.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON object from *path*, returning ``{}`` if it doesn't exist.

    Raises ``ValueError`` with a clear message if the file exists but is
    corrupt, so a malformed store fails loudly instead of surfacing a raw
    decode error.
    """
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Invalid JSON in {path}: {exc}") from exc


def save_json(path: Path, data: dict[str, Any]) -> None:
    """Write *data* to *path* atomically as UTF-8 JSON."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp, path)
