"""Re-export of the shared JSON persistence helpers for CLI entity stores.

The implementation lives in :mod:`miminions.core.persistence` so that both
``core`` (e.g. bootstrap) and ``cli`` modules can use a single copy. CLI
modules import these from here for convenience.
"""

from miminions.core.persistence import load_json, save_json  # noqa: F401

__all__ = ["load_json", "save_json"]
