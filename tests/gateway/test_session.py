"""Unit tests for gateway.session module."""
import json
import pytest
import tempfile
from datetime import datetime
from pathlib import Path

from miminions.core.gateway.session import (
    Session,
    SessionManager,
    SessionMessage,
    _safe_filename,
)


# ── SessionMessage tests ─────────────────────────────────────────────


class TestSessionMessage:
    """Tests for SessionMessage dataclass."""

    def test_creation_required_fields(self):
        msg = SessionMessage(role="user", content="hello")
        assert msg.role == "user"
        assert msg.content == "hello"

    def test_defaults(self):
        msg = SessionMessage(role="user", content="")
        assert msg.channel == ""
        assert msg.sender_id is None
        assert msg.chat_id is None
        assert isinstance(msg.timestamp, str)
        assert msg.media == []
        assert msg.metadata == {}

    def test_to_dict(self):
        msg = SessionMessage(
            role="user",
            content="hi",
            channel="telegram",
            sender_id="u1",
            chat_id="c1",
            media=["url"],
            metadata={"k": "v"},
        )
        d = msg.to_dict()
        assert d["role"] == "user"
        assert d["content"] == "hi"
        assert d["channel"] == "telegram"
        assert d["sender_id"] == "u1"
        assert d["chat_id"] == "c1"
        assert d["media"] == ["url"]
        assert d["metadata"] == {"k": "v"}
        assert "timestamp" in d

    def test_from_dict(self):
        data = {
            "role": "assistant",
            "content": "reply",
            "channel": "discord",
            "sender_id": "bot",
            "chat_id": "c2",
            "timestamp": "2025-01-01T00:00:00",
            "media": [],
            "metadata": {"x": 1},
        }
        msg = SessionMessage.from_dict(data)
        assert msg.role == "assistant"
        assert msg.content == "reply"
        assert msg.channel == "discord"
        assert msg.sender_id == "bot"
        assert msg.chat_id == "c2"
        assert msg.metadata == {"x": 1}

    def test_from_dict_missing_keys(self):
        """from_dict should handle missing keys gracefully."""
        msg = SessionMessage.from_dict({})
        assert msg.role == ""
        assert msg.content == ""
        assert msg.channel == ""
        assert msg.sender_id is None
        assert msg.chat_id is None
        assert msg.media == []
        assert msg.metadata == {}

    def test_roundtrip(self):
        original = SessionMessage(
            role="user", content="test", channel="ws", sender_id="s"
        )
        restored = SessionMessage.from_dict(original.to_dict())
        assert restored.role == original.role
        assert restored.content == original.content
        assert restored.channel == original.channel
        assert restored.sender_id == original.sender_id


# ── Session tests ────────────────────────────────────────────────────


class TestSession:
    """Tests for Session dataclass."""

    def test_creation(self):
        s = Session(key="test:123")
        assert s.key == "test:123"
        assert s.messages == []
        assert isinstance(s.created_at, datetime)
        assert isinstance(s.updated_at, datetime)
        assert s.metadata == {}

    def test_add_message(self):
        s = Session(key="k")
        s.add_message("user", "hello", channel="tg", sender_id="u1")

        assert len(s.messages) == 1
        msg = s.messages[0]
        assert msg["role"] == "user"
        assert msg["content"] == "hello"
        assert msg["channel"] == "tg"
        assert msg["sender_id"] == "u1"

    def test_add_message_updates_timestamp(self):
        s = Session(key="k")
        before = s.updated_at
        s.add_message("user", "hi")
        assert s.updated_at >= before

    def test_add_multiple_messages(self):
        s = Session(key="k")
        s.add_message("user", "one")
        s.add_message("assistant", "two")
        s.add_message("user", "three")
        assert len(s.messages) == 3

    def test_get_history_default(self):
        s = Session(key="k")
        s.add_message("user", "a")
        s.add_message("assistant", "b")
        history = s.get_history()
        assert len(history) == 2

    def test_get_history_max_messages(self):
        s = Session(key="k")
        for i in range(10):
            s.add_message("user", f"msg-{i}")
        history = s.get_history(max_messages=3)
        assert len(history) == 3
        assert history[0]["content"] == "msg-7"

    def test_get_history_aligns_to_user_turn(self):
        """Should drop leading non-user messages."""
        s = Session(key="k")
        s.add_message("assistant", "orphaned")
        s.add_message("user", "start")
        s.add_message("assistant", "reply")

        history = s.get_history()
        assert history[0]["role"] == "user"
        assert len(history) == 2

    def test_get_history_empty(self):
        s = Session(key="k")
        assert s.get_history() == []

    def test_get_history_no_user_messages(self):
        """All non-user messages; should still return something."""
        s = Session(key="k")
        s.add_message("system", "init")
        s.add_message("assistant", "hi")
        # No user turn to align to, returns all
        history = s.get_history()
        assert len(history) == 2

    def test_clear(self):
        s = Session(key="k")
        s.add_message("user", "a")
        s.add_message("user", "b")
        assert len(s.messages) == 2

        s.clear()
        assert s.messages == []

    def test_clear_updates_timestamp(self):
        s = Session(key="k")
        before = s.updated_at
        s.clear()
        assert s.updated_at >= before

    def test_add_message_with_kwargs(self):
        """Extra kwargs like media and metadata should be included."""
        s = Session(key="k")
        s.add_message("user", "pic", media=["url.jpg"], metadata={"k": "v"})
        msg = s.messages[0]
        assert msg["media"] == ["url.jpg"]
        assert msg["metadata"] == {"k": "v"}


# ── _safe_filename tests ─────────────────────────────────────────────


class TestSafeFilename:
    def test_colon_replaced(self):
        assert _safe_filename("telegram:123") == "telegram_123"

    def test_slash_replaced(self):
        assert _safe_filename("a/b") == "a_b"

    def test_backslash_replaced(self):
        assert _safe_filename("a\\b") == "a_b"

    def test_multiple_replacements(self):
        assert _safe_filename("ch:id/sub\\x") == "ch_id_sub_x"

    def test_no_special_chars(self):
        assert _safe_filename("simple") == "simple"


# ── SessionManager tests ─────────────────────────────────────────────


class TestSessionManagerInit:
    def test_creates_storage_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sessions"
            assert not path.exists()
            mgr = SessionManager(path)
            assert path.exists()

    def test_string_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            assert isinstance(mgr.storage_path, Path)


class TestSessionManagerGetOrCreate:
    def test_create_new_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("new:key")
            assert s.key == "new:key"
            assert s.messages == []

    def test_cached_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s1 = mgr.get_or_create("k")
            s2 = mgr.get_or_create("k")
            assert s1 is s2

    def test_loads_from_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("k")
            s.add_message("user", "persisted")
            mgr.save(s)

            mgr.invalidate("k")
            s2 = mgr.get_or_create("k")
            assert s2 is not s
            assert len(s2.messages) == 1
            assert s2.messages[0]["content"] == "persisted"


class TestSessionManagerSave:
    def test_save_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("save:test")
            s.add_message("user", "hi")
            mgr.save(s)

            path = mgr._get_session_path("save:test")
            assert path.exists()

    def test_save_jsonl_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("fmt")
            s.add_message("user", "one")
            s.add_message("assistant", "two")
            mgr.save(s)

            path = mgr._get_session_path("fmt")
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            assert len(lines) == 3  # 1 metadata + 2 messages

            metadata = json.loads(lines[0])
            assert metadata["_type"] == "metadata"
            assert metadata["key"] == "fmt"

            msg1 = json.loads(lines[1])
            assert msg1["role"] == "user"
            assert msg1["content"] == "one"

    def test_save_updates_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("k")
            mgr.save(s)
            assert mgr._cache["k"] is s


class TestSessionManagerLoad:
    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            assert mgr._load("nonexistent") is None

    def test_load_corrupted_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            path = mgr._get_session_path("bad")
            path.write_text("not valid json\n", encoding="utf-8")
            assert mgr._load("bad") is None

    def test_load_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("meta")
            s.metadata = {"version": 2}
            s.add_message("user", "x")
            mgr.save(s)

            mgr.invalidate("meta")
            s2 = mgr.get_or_create("meta")
            assert s2.metadata == {"version": 2}

    def test_load_preserves_created_at(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("ts")
            original_created = s.created_at
            s.add_message("user", "x")
            mgr.save(s)

            mgr.invalidate("ts")
            s2 = mgr.get_or_create("ts")
            assert s2.created_at.isoformat() == original_created.isoformat()

    def test_load_skips_blank_lines(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            path = mgr._get_session_path("blanks")
            content = (
                json.dumps({"_type": "metadata", "key": "blanks", "created_at": "2025-01-01T00:00:00"})
                + "\n\n"
                + json.dumps({"role": "user", "content": "hi"})
                + "\n\n"
            )
            path.write_text(content, encoding="utf-8")

            s = mgr._load("blanks")
            assert s is not None
            assert len(s.messages) == 1

    def test_load_without_created_at(self):
        """Metadata line without created_at should still load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            path = mgr._get_session_path("nodate")
            content = json.dumps({"_type": "metadata", "key": "nodate"}) + "\n"
            path.write_text(content, encoding="utf-8")

            s = mgr._load("nodate")
            assert s is not None
            assert isinstance(s.created_at, datetime)


class TestSessionManagerInvalidate:
    def test_invalidate_removes_from_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            mgr.get_or_create("k")
            assert "k" in mgr._cache

            mgr.invalidate("k")
            assert "k" not in mgr._cache

    def test_invalidate_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            mgr.invalidate("nope")  # Should not raise


class TestSessionManagerDelete:
    def test_delete_existing(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("del")
            mgr.save(s)

            assert mgr.delete("del") is True
            assert not mgr._get_session_path("del").exists()
            assert "del" not in mgr._cache

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            assert mgr.delete("nope") is False

    def test_delete_cached_only(self):
        """Delete should clear cache even if no file on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            mgr.get_or_create("cached_only")
            assert "cached_only" in mgr._cache

            result = mgr.delete("cached_only")
            assert result is False  # no file to delete
            assert "cached_only" not in mgr._cache


class TestSessionManagerListSessions:
    def test_list_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            assert mgr.list_sessions() == []

    def test_list_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            for key in ["a:1", "b:2", "c:3"]:
                s = mgr.get_or_create(key)
                s.add_message("user", f"msg-{key}")
                mgr.save(s)

            sessions = mgr.list_sessions()
            assert len(sessions) == 3
            keys = [s["key"] for s in sessions]
            assert set(keys) == {"a:1", "b:2", "c:3"}

    def test_list_sorted_by_updated_at(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)

            s1 = mgr.get_or_create("first")
            s1.add_message("user", "old")
            mgr.save(s1)

            s2 = mgr.get_or_create("second")
            s2.add_message("user", "new")
            mgr.save(s2)

            sessions = mgr.list_sessions()
            assert sessions[0]["key"] == "second"  # Most recent first

    def test_list_ignores_non_jsonl_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            (Path(tmpdir) / "random.txt").write_text("not a session")

            assert mgr.list_sessions() == []

    def test_list_handles_corrupted_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            (Path(tmpdir) / "bad.jsonl").write_text("{{invalid json")

            # Should not crash, just skip
            sessions = mgr.list_sessions()
            assert sessions == []
