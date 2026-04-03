"""Unit tests for gateway.config module."""

import json
import pytest
from pathlib import Path

from miminions.core.gateway.config import (
    BusConfig,
    ChannelConfig,
    CronConfig,
    GatewayConfig,
    SessionConfig,
)


# ── Defaults ─────────────────────────────────────────────────────────


class TestBusConfigDefaults:
    def test_default_max_queue_size(self):
        cfg = BusConfig()
        assert cfg.max_queue_size == 1000

    def test_custom_max_queue_size(self):
        cfg = BusConfig(max_queue_size=500)
        assert cfg.max_queue_size == 500


class TestSessionConfigDefaults:
    def test_default_storage_dir(self):
        cfg = SessionConfig()
        assert cfg.storage_dir == "sessions"

    def test_default_ttl(self):
        cfg = SessionConfig()
        assert cfg.ttl_seconds == 3600

    def test_custom_values(self):
        cfg = SessionConfig(storage_dir="my_sessions", ttl_seconds=7200)
        assert cfg.storage_dir == "my_sessions"
        assert cfg.ttl_seconds == 7200


class TestCronConfigDefaults:
    def test_default_store_file(self):
        cfg = CronConfig()
        assert cfg.store_file == "jobs.json"

    def test_default_enabled(self):
        cfg = CronConfig()
        assert cfg.enabled is True

    def test_disabled(self):
        cfg = CronConfig(enabled=False)
        assert cfg.enabled is False


class TestChannelConfig:
    def test_requires_kind(self):
        cfg = ChannelConfig(kind="websocket")
        assert cfg.kind == "websocket"

    def test_default_enabled(self):
        cfg = ChannelConfig(kind="http")
        assert cfg.enabled is True

    def test_default_allow_from(self):
        cfg = ChannelConfig(kind="http")
        assert cfg.allow_from == ["*"]

    def test_default_options_empty(self):
        cfg = ChannelConfig(kind="http")
        assert cfg.options == {}

    def test_custom_options(self):
        cfg = ChannelConfig(
            kind="websocket",
            enabled=False,
            allow_from=["user1", "user2"],
            options={"host": "0.0.0.0", "port": 8765},
        )
        assert cfg.kind == "websocket"
        assert cfg.enabled is False
        assert cfg.allow_from == ["user1", "user2"]
        assert cfg.options["port"] == 8765


# ── GatewayConfig ────────────────────────────────────────────────────


class TestGatewayConfigDefaults:
    def test_default_data_dir(self):
        cfg = GatewayConfig()
        assert cfg.data_dir == Path("~/.miminions/gateway")

    def test_default_log_level(self):
        cfg = GatewayConfig()
        assert cfg.log_level == "INFO"

    def test_default_sub_configs(self):
        cfg = GatewayConfig()
        assert isinstance(cfg.bus, BusConfig)
        assert isinstance(cfg.sessions, SessionConfig)
        assert isinstance(cfg.cron, CronConfig)
        assert cfg.channels == {}


class TestGatewayConfigPaths:
    def test_resolve_path(self, tmp_path):
        cfg = GatewayConfig(data_dir=tmp_path / "gw")
        resolved = cfg.resolve_path("sub/dir")
        assert resolved == tmp_path / "gw" / "sub" / "dir"

    def test_sessions_path(self, tmp_path):
        cfg = GatewayConfig(data_dir=tmp_path / "gw")
        assert cfg.sessions_path == tmp_path / "gw" / "sessions"

    def test_sessions_path_custom(self, tmp_path):
        cfg = GatewayConfig(
            data_dir=tmp_path / "gw",
            sessions=SessionConfig(storage_dir="my_sessions"),
        )
        assert cfg.sessions_path == tmp_path / "gw" / "my_sessions"

    def test_cron_store_path(self, tmp_path):
        cfg = GatewayConfig(data_dir=tmp_path / "gw")
        assert cfg.cron_store_path == tmp_path / "gw" / "jobs.json"

    def test_cron_store_path_custom(self, tmp_path):
        cfg = GatewayConfig(
            data_dir=tmp_path / "gw",
            cron=CronConfig(store_file="cron/store.json"),
        )
        assert cfg.cron_store_path == tmp_path / "gw" / "cron" / "store.json"

    def test_tilde_expansion(self):
        cfg = GatewayConfig()
        resolved = cfg.sessions_path
        assert "~" not in str(resolved)


# ── Serialization round-trip ─────────────────────────────────────────


class TestGatewayConfigSerialization:
    def _full_config(self, tmp_path) -> GatewayConfig:
        return GatewayConfig(
            data_dir=tmp_path / "gw",
            log_level="DEBUG",
            bus=BusConfig(max_queue_size=500),
            sessions=SessionConfig(storage_dir="sess", ttl_seconds=1800),
            cron=CronConfig(store_file="cron.json", enabled=False),
            channels={
                "ws": ChannelConfig(
                    kind="websocket",
                    enabled=True,
                    allow_from=["u1"],
                    options={"port": 8765},
                ),
                "http": ChannelConfig(
                    kind="http",
                    enabled=False,
                    allow_from=["*"],
                    options={"host": "0.0.0.0"},
                ),
            },
        )

    def test_to_dict(self, tmp_path):
        cfg = self._full_config(tmp_path)
        d = cfg.to_dict()

        assert d["data_dir"] == str(tmp_path / "gw")
        assert d["log_level"] == "DEBUG"
        assert d["bus"]["max_queue_size"] == 500
        assert d["sessions"]["storage_dir"] == "sess"
        assert d["sessions"]["ttl_seconds"] == 1800
        assert d["cron"]["store_file"] == "cron.json"
        assert d["cron"]["enabled"] is False
        assert "ws" in d["channels"]
        assert d["channels"]["ws"]["kind"] == "websocket"
        assert d["channels"]["ws"]["options"]["port"] == 8765
        assert d["channels"]["http"]["enabled"] is False

    def test_roundtrip(self, tmp_path):
        original = self._full_config(tmp_path)
        d = original.to_dict()
        restored = GatewayConfig.from_dict(d)

        assert restored.data_dir == original.data_dir
        assert restored.log_level == original.log_level
        assert restored.bus.max_queue_size == original.bus.max_queue_size
        assert restored.sessions.storage_dir == original.sessions.storage_dir
        assert restored.sessions.ttl_seconds == original.sessions.ttl_seconds
        assert restored.cron.store_file == original.cron.store_file
        assert restored.cron.enabled == original.cron.enabled
        assert len(restored.channels) == 2
        assert restored.channels["ws"].kind == "websocket"
        assert restored.channels["ws"].options["port"] == 8765
        assert restored.channels["http"].enabled is False

    def test_roundtrip_json(self, tmp_path):
        original = self._full_config(tmp_path)
        json_str = json.dumps(original.to_dict())
        restored = GatewayConfig.from_dict(json.loads(json_str))

        assert restored.log_level == "DEBUG"
        assert restored.bus.max_queue_size == 500
        assert len(restored.channels) == 2

    def test_from_dict_defaults(self):
        """from_dict with empty dict should use defaults."""
        cfg = GatewayConfig.from_dict({})
        assert cfg.log_level == "INFO"
        assert cfg.bus.max_queue_size == 1000
        assert cfg.sessions.storage_dir == "sessions"
        assert cfg.cron.enabled is True
        assert cfg.channels == {}

    def test_from_dict_partial(self):
        """from_dict with partial data fills in defaults."""
        cfg = GatewayConfig.from_dict({
            "log_level": "WARNING",
            "bus": {"max_queue_size": 2000},
        })
        assert cfg.log_level == "WARNING"
        assert cfg.bus.max_queue_size == 2000
        assert cfg.sessions.ttl_seconds == 3600  # default


# ── Channel isolation ────────────────────────────────────────────────


class TestChannelConfigIsolation:
    def test_separate_channel_instances(self):
        """Each GatewayConfig gets its own channels dict."""
        cfg1 = GatewayConfig()
        cfg2 = GatewayConfig()
        cfg1.channels["ws"] = ChannelConfig(kind="websocket")
        assert "ws" not in cfg2.channels

    def test_separate_allow_from_lists(self):
        """Each ChannelConfig gets its own allow_from list."""
        ch1 = ChannelConfig(kind="a")
        ch2 = ChannelConfig(kind="b")
        ch1.allow_from.append("user1")
        assert "user1" not in ch2.allow_from
