"""Data export/import commands for MiMinions CLI."""

from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import click

from miminions.utils.json_io import load_json, save_json

from .auth import get_config_dir

_DATA_FILES = {
    "agents": "agents.json",
    "tasks": "tasks.json",
    "knowledge": "knowledge.json",
}


def _load_data_sections(config_dir: Path) -> dict[str, dict[str, Any]]:
    payload: dict[str, dict[str, Any]] = {}
    for key, filename in _DATA_FILES.items():
        raw = load_json(config_dir / filename)
        if not isinstance(raw, dict):
            raise click.ClickException(f"Invalid {filename}: expected a JSON object")
        payload[key] = raw
    return payload


@click.command("export")
@click.option("--output", "output_path", required=True, help="Path to write backup JSON file.")
def export_data(output_path: str) -> None:
    """Export agents/tasks/knowledge to a single JSON backup file."""
    config_dir = get_config_dir()
    payload = {
        "version": 1,
        "exported_at": datetime.now(UTC).isoformat(),
        **_load_data_sections(config_dir),
    }

    out = Path(output_path).expanduser().resolve()
    save_json(out, payload, ensure_parent=True)
    click.echo(f"Exported data to {out}")


@click.command("import")
@click.option("--input", "input_path", required=True, help="Path to backup JSON file.")
@click.option(
    "--mode",
    type=click.Choice(["merge", "replace"]),
    default="merge",
    show_default=True,
    help="Import strategy for agents/tasks/knowledge records.",
)
def import_data(input_path: str, mode: str) -> None:
    """Import agents/tasks/knowledge from a JSON backup file."""
    config_dir = get_config_dir()

    path = Path(input_path).expanduser().resolve()
    if not path.exists():
        raise click.ClickException(f"Backup file not found: {path}")

    data = load_json(path)
    if not isinstance(data, dict):
        raise click.ClickException("Invalid backup file: expected a JSON object")

    for key in _DATA_FILES:
        if key in data and not isinstance(data[key], dict):
            raise click.ClickException(f"Invalid backup file: '{key}' must be a JSON object")

    current = _load_data_sections(config_dir)

    imported_counts: dict[str, int] = {}
    for key, filename in _DATA_FILES.items():
        incoming = data.get(key, {})
        base = {} if mode == "replace" else current[key].copy()
        base.update(incoming)

        save_json(config_dir / filename, base, ensure_parent=True)
        imported_counts[key] = len(incoming)

    click.echo(
        "Imported data "
        f"(mode={mode}): agents={imported_counts['agents']}, "
        f"tasks={imported_counts['tasks']}, "
        f"knowledge={imported_counts['knowledge']}"
    )
