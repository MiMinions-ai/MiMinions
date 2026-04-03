"""Gateway configuration with scoped ownership.

Each dataclass owns one layer of the gateway stack.  Paths inside
sub-configs are stored as *relative* strings and resolved against
``GatewayConfig.data_dir`` at runtime so the same config file is
portable across machines.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


# ── Sub-configs ──────────────────────────────────────────────────────


@dataclass
class BusConfig:
    """MessageBus configuration."""

    max_queue_size: int = 1000


@dataclass
class SessionConfig:
    """SessionManager configuration.

    ``storage_dir`` is relative to ``GatewayConfig.data_dir``.
    """

    storage_dir: str = "sessions"
    ttl_seconds: float = 3600


@dataclass
class CronConfig:
    """CronService configuration.

    ``store_file`` is relative to ``GatewayConfig.data_dir``.
    """

    store_file: str = "jobs.json"
    enabled: bool = True


@dataclass
class ChannelConfig:
    """Per-channel configuration.

    ``kind`` selects the concrete ``BaseChannel`` subclass (e.g.
    ``"websocket"``, ``"http"``, ``"telegram"``).  ``options`` carries
    channel-specific parameters (host, port, token, …).
    """

    kind: str
    enabled: bool = True
    allow_from: list[str] = field(default_factory=lambda: ["*"])
    options: dict[str, Any] = field(default_factory=dict)


# ── Root config ──────────────────────────────────────────────────────


@dataclass
class GatewayConfig:
    """Top-level gateway daemon configuration.

    Owns the shared ``data_dir`` and delegates to per-component
    sub-configs.  Use :meth:`resolve_path` (or the convenience
    properties) to turn relative paths into absolute ones.
    """

    data_dir: Path = field(
        default_factory=lambda: Path("~/.miminions/gateway")
    )
    log_level: str = "INFO"
    bus: BusConfig = field(default_factory=BusConfig)
    sessions: SessionConfig = field(default_factory=SessionConfig)
    cron: CronConfig = field(default_factory=CronConfig)
    channels: dict[str, ChannelConfig] = field(default_factory=dict)

    # ── Path helpers ─────────────────────────────────────────────────

    def resolve_path(self, relative: str) -> Path:
        """Resolve *relative* against the expanded ``data_dir``."""
        return self.data_dir.expanduser().resolve() / relative

    @property
    def sessions_path(self) -> Path:
        """Absolute path to the sessions storage directory."""
        return self.resolve_path(self.sessions.storage_dir)

    @property
    def cron_store_path(self) -> Path:
        """Absolute path to the cron job store file."""
        return self.resolve_path(self.cron.store_file)

    # ── Serialization ────────────────────────────────────────────────

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a plain dict (suitable for JSON/TOML)."""
        return {
            "data_dir": str(self.data_dir),
            "log_level": self.log_level,
            "bus": {
                "max_queue_size": self.bus.max_queue_size,
            },
            "sessions": {
                "storage_dir": self.sessions.storage_dir,
                "ttl_seconds": self.sessions.ttl_seconds,
            },
            "cron": {
                "store_file": self.cron.store_file,
                "enabled": self.cron.enabled,
            },
            "channels": {
                name: {
                    "kind": ch.kind,
                    "enabled": ch.enabled,
                    "allow_from": ch.allow_from,
                    "options": ch.options,
                }
                for name, ch in self.channels.items()
            },
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> GatewayConfig:
        """Deserialize from a plain dict."""
        bus_data = data.get("bus", {})
        sess_data = data.get("sessions", {})
        cron_data = data.get("cron", {})
        ch_data = data.get("channels", {})

        channels: dict[str, ChannelConfig] = {}
        for name, ch in ch_data.items():
            channels[name] = ChannelConfig(
                kind=ch["kind"],
                enabled=ch.get("enabled", True),
                allow_from=ch.get("allow_from", ["*"]),
                options=ch.get("options", {}),
            )

        return cls(
            data_dir=Path(data["data_dir"]) if "data_dir" in data else Path("~/.miminions/gateway"),
            log_level=data.get("log_level", "INFO"),
            bus=BusConfig(
                max_queue_size=bus_data.get("max_queue_size", 1000),
            ),
            sessions=SessionConfig(
                storage_dir=sess_data.get("storage_dir", "sessions"),
                ttl_seconds=sess_data.get("ttl_seconds", 3600),
            ),
            cron=CronConfig(
                store_file=cron_data.get("store_file", "jobs.json"),
                enabled=cron_data.get("enabled", True),
            ),
            channels=channels,
        )
