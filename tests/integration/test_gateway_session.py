"""Unit tests for gateway.session module."""
import json
import logging
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
        assert msg.role == "user", f"expect SessionMessage preserves required role value from constructor input as 'user', got {msg.role}"
        assert msg.content == "hello", f"expect SessionMessage preserves required content value from constructor input as 'hello', got {msg.content}"

    def test_defaults(self):
        msg = SessionMessage(role="user", content="")
        assert msg.channel == "", f"expect SessionMessage default channel is empty string when not provided as '', got {msg.channel}"
        assert msg.sender_id is None, f"expect SessionMessage default sender_id is None when not provided, got {msg.sender_id}"
        assert msg.chat_id is None, f"expect SessionMessage default chat_id is None when not provided, got {msg.chat_id}"
        timestamp_is_string = isinstance(msg.timestamp, str)
        timestamp_type = type(msg.timestamp)
        assert timestamp_is_string, f"expect session message timestamp to be string as True, got {timestamp_type}"
        assert msg.media == [], f"expect SessionMessage default media list is empty when not provided as [], got {msg.media}"
        assert msg.metadata == {}, f"expect SessionMessage default metadata mapping is empty when not provided as {{}}, got {msg.metadata}"

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
        assert d["role"] == "user", f"expect SessionMessage.to_dict includes role field value from message object as 'user', got {d['role']}"
        assert d["content"] == "hi", f"expect SessionMessage.to_dict includes content field value from message object as 'hi', got {d['content']}"
        assert d["channel"] == "telegram", f"expect SessionMessage.to_dict includes channel field value from message object as 'telegram', got {d['channel']}"
        assert d["sender_id"] == "u1", f"expect SessionMessage.to_dict includes sender_id field value from message object as 'u1', got {d['sender_id']}"
        assert d["chat_id"] == "c1", f"expect SessionMessage.to_dict includes chat_id field value from message object as 'c1', got {d['chat_id']}"
        assert d["media"] == ["url"], f"expect ['url'], got {d['media']}"
        assert d["metadata"] == {"k": "v"}, f"expect {{'k': 'v'}}, got {d['metadata']}"
        assert "timestamp" in d, f"expect contains 'timestamp', got {d}"

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
        assert msg.role == "assistant", f"expect SessionMessage.from_dict restores role from serialized payload as 'assistant', got {msg.role}"
        assert msg.content == "reply", f"expect SessionMessage.from_dict restores content from serialized payload as 'reply', got {msg.content}"
        assert msg.channel == "discord", f"expect SessionMessage.from_dict restores channel from serialized payload as 'discord', got {msg.channel}"
        assert msg.sender_id == "bot", f"expect SessionMessage.from_dict restores sender_id from serialized payload as 'bot', got {msg.sender_id}"
        assert msg.chat_id == "c2", f"expect SessionMessage.from_dict restores chat_id from serialized payload as 'c2', got {msg.chat_id}"
        assert msg.metadata == {"x": 1}, f"expect {{'x': 1}}, got {msg.metadata}"

    def test_from_dict_missing_keys(self):
        """from_dict should handle missing keys gracefully."""
        msg = SessionMessage.from_dict({})
        assert msg.role == "", f"expect SessionMessage.from_dict uses empty default role when key is missing as '', got {msg.role}"
        assert msg.content == "", f"expect SessionMessage.from_dict uses empty default content when key is missing as '', got {msg.content}"
        assert msg.channel == "", f"expect SessionMessage.from_dict uses empty default channel when key is missing as '', got {msg.channel}"
        assert msg.sender_id is None, f"expect SessionMessage.from_dict uses None default sender_id when key is missing, got {msg.sender_id}"
        assert msg.chat_id is None, f"expect SessionMessage.from_dict uses None default chat_id when key is missing, got {msg.chat_id}"
        assert msg.media == [], f"expect SessionMessage.from_dict uses empty default media list when key is missing as [], got {msg.media}"
        assert msg.metadata == {}, f"expect SessionMessage.from_dict uses empty default metadata mapping when key is missing as {{}}, got {msg.metadata}"

    def test_roundtrip(self):
        original = SessionMessage(
            role="user", content="test", channel="ws", sender_id="s"
        )
        restored = SessionMessage.from_dict(original.to_dict())
        assert restored.role == original.role, f"expect original.role as {original.role}, got {restored.role}"
        assert restored.content == original.content, f"expect original.content as {original.content}, got {restored.content}"
        assert restored.channel == original.channel, f"expect original.channel as {original.channel}, got {restored.channel}"
        assert restored.sender_id == original.sender_id, f"expect original.sender_id as {original.sender_id}, got {restored.sender_id}"


# ── Session tests ────────────────────────────────────────────────────


class TestSession:
    """Tests for Session dataclass."""

    def test_creation(self):
        s = Session(key="test:123")
        assert s.key == "test:123", f"expect Session key is preserved from constructor input as 'test:123', got {s.key}"
        assert s.messages == [], f"expect Session starts with empty message history on creation as [], got {s.messages}"
        created_at_is_datetime = isinstance(s.created_at, datetime)
        created_at_type = type(s.created_at)
        assert created_at_is_datetime, f"expect session created_at to be datetime as True, got {created_at_type}"
        updated_at_is_datetime = isinstance(s.updated_at, datetime)
        updated_at_type = type(s.updated_at)
        assert updated_at_is_datetime, f"expect session updated_at to be datetime as True, got {updated_at_type}"
        assert s.metadata == {}, f"expect Session starts with empty metadata mapping on creation as {{}}, got {s.metadata}"

    def test_add_message(self):
        s = Session(key="k")
        s.add_message("user", "hello", channel="tg", sender_id="u1")

        message_count = len(s.messages)
        assert message_count == 1, f"expect add_message appends exactly one message entry for one call as 1, got {message_count}"
        msg = s.messages[0]
        assert msg["role"] == "user", f"expect add_message stores provided role value in appended history entry as 'user', got {msg['role']}"
        assert msg["content"] == "hello", f"expect add_message stores provided content value in appended history entry as 'hello', got {msg['content']}"
        assert msg["channel"] == "tg", f"expect add_message stores provided channel value in appended history entry as 'tg', got {msg['channel']}"
        assert msg["sender_id"] == "u1", f"expect add_message stores provided sender_id value in appended history entry as 'u1', got {msg['sender_id']}"

    def test_add_message_updates_timestamp(self):
        s = Session(key="k")
        before = s.updated_at
        s.add_message("user", "hi")
        assert s.updated_at >= before, f"expect s.updated_at >= before as {before}, got {s.updated_at}"

    def test_add_multiple_messages(self):
        s = Session(key="k")
        s.add_message("user", "one")
        s.add_message("assistant", "two")
        s.add_message("user", "three")
        message_count = len(s.messages)
        assert message_count == 3, f"expect three add_message calls produce three stored session messages as 3, got {message_count}"

    def test_get_history_default(self):
        s = Session(key="k")
        s.add_message("user", "a")
        s.add_message("assistant", "b")
        history = s.get_history()
        history_count = len(history)
        assert history_count == 2, f"expect get_history returns all messages when max_messages is not set as 2, got {history_count}"

    def test_get_history_max_messages(self):
        s = Session(key="k")
        for i in range(10):
            s.add_message("user", f"msg-{i}")
        history = s.get_history(max_messages=3)
        history_count = len(history)
        assert history_count == 3, f"expect get_history(max_messages=3) truncates to three newest messages as 3, got {history_count}"
        assert history[0]["content"] == "msg-7", f"expect get_history(max_messages=3) returns latest window beginning at msg-7, got {history[0]['content']}"

    def test_get_history_aligns_to_user_turn(self):
        """Should drop leading non-user messages."""
        s = Session(key="k")
        s.add_message("assistant", "orphaned")
        s.add_message("user", "start")
        s.add_message("assistant", "reply")

        history = s.get_history()
        assert history[0]["role"] == "user", f"expect get_history aligns trimmed history to first user turn as 'user', got {history[0]['role']}"
        history_count = len(history)
        assert history_count == 2, f"expect user-turn alignment drops leading orphaned assistant message leaving two messages as 2, got {history_count}"

    def test_get_history_empty(self):
        s = Session(key="k")
        history = s.get_history()
        assert history == [], f"expect get_history returns empty list when session has no messages as [], got {history}"

    def test_get_history_no_user_messages(self):
        """All non-user messages; should still return something."""
        s = Session(key="k")
        s.add_message("system", "init")
        s.add_message("assistant", "hi")
        # No user turn to align to, returns all
        history = s.get_history()
        history_count = len(history)
        assert history_count == 2, f"expect get_history keeps all messages when no user turn exists for alignment as 2, got {history_count}"

    def test_clear(self):
        s = Session(key="k")
        s.add_message("user", "a")
        s.add_message("user", "b")
        message_count = len(s.messages)
        assert message_count == 2, f"expect precondition before clear has two stored messages as 2, got {message_count}"

        s.clear()
        assert s.messages == [], f"expect clear removes all messages from session history as [], got {s.messages}"

    def test_clear_updates_timestamp(self):
        s = Session(key="k")
        before = s.updated_at
        s.clear()
        assert s.updated_at >= before, f"expect s.updated_at >= before as {before}, got {s.updated_at}"

    def test_add_message_with_kwargs(self):
        """Extra kwargs like media and metadata should be included."""
        s = Session(key="k")
        s.add_message("user", "pic", media=["url.jpg"], metadata={"k": "v"})
        msg = s.messages[0]
        assert msg["media"] == ["url.jpg"], f"expect ['url.jpg'], got {msg['media']}"
        assert msg["metadata"] == {"k": "v"}, f"expect {{'k': 'v'}}, got {msg['metadata']}"


# ── _safe_filename tests ─────────────────────────────────────────────


class TestSafeFilename:
    def test_colon_replaced(self):
        safe_name = _safe_filename("telegram:123")
        assert safe_name == "telegram_123", f"expect _safe_filename replaces colon with underscore for filesystem-safe key as 'telegram_123', got {safe_name}"

    def test_slash_replaced(self):
        safe_name = _safe_filename("a/b")
        assert safe_name == "a_b", f"expect _safe_filename replaces forward slash with underscore for filesystem-safe key as 'a_b', got {safe_name}"

    def test_backslash_replaced(self):
        safe_name = _safe_filename("a\\b")
        assert safe_name == "a_b", f"expect _safe_filename replaces backslash with underscore for filesystem-safe key as 'a_b', got {safe_name}"

    def test_multiple_replacements(self):
        safe_name = _safe_filename("ch:id/sub\\x")
        assert safe_name == "ch_id_sub_x", f"expect _safe_filename replaces all reserved separators in composite key as 'ch_id_sub_x', got {safe_name}"

    def test_no_special_chars(self):
        safe_name = _safe_filename("simple")
        assert safe_name == "simple", f"expect _safe_filename leaves already-safe keys unchanged as 'simple', got {safe_name}"


# ── SessionManager tests ─────────────────────────────────────────────


class TestSessionManagerInit:
    def test_creates_storage_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            path = Path(tmpdir) / "sessions"
            storage_dir_exists_before_init = path.exists()
            assert not storage_dir_exists_before_init, f"expect session storage dir absent before SessionManager init as False, got {storage_dir_exists_before_init}"
            SessionManager(path)
            storage_dir_exists_after_init = path.exists()
            assert storage_dir_exists_after_init, f"expect SessionManager init creates storage directory as True, got {storage_dir_exists_after_init}"

    def test_string_path(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            storage_path_is_path = isinstance(mgr.storage_path, Path)
            storage_path_type = type(mgr.storage_path)
            assert storage_path_is_path, f"expect SessionManager storage_path to be Path as True, got {storage_path_type}"


class TestSessionManagerGetOrCreate:
    def test_create_new_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("new:key")
            assert s.key == "new:key", f"expect get_or_create returns session with requested key for new session path as 'new:key', got {s.key}"
            assert s.messages == [], f"expect get_or_create initializes new session with empty message history as [], got {s.messages}"

    def test_cached_session(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s1 = mgr.get_or_create("k")
            s2 = mgr.get_or_create("k")
            assert s1 is s2, f"expect s2 as {s2}, got {s1}"

    def test_loads_from_disk(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("k")
            s.add_message("user", "persisted")
            mgr.save(s)

            mgr.invalidate("k")
            s2 = mgr.get_or_create("k")
            assert s2 is not s, f"expect value is not s as {s}, got {s2}"
            message_count = len(s2.messages)
            assert message_count == 1, f"expect get_or_create reloads one persisted message from disk after invalidate as 1, got {message_count}"
            assert s2.messages[0]["content"] == "persisted", f"expect get_or_create loads persisted message content from disk after cache invalidation as 'persisted', got {s2.messages[0]['content']}"


class TestSessionManagerSave:
    def test_save_creates_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("save:test")
            s.add_message("user", "hi")
            mgr.save(s)

            path = mgr._get_session_path("save:test")
            saved_file_exists = path.exists()
            assert saved_file_exists, f"expect save creates session file on disk as True, got {saved_file_exists}"

    def test_save_jsonl_format(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("fmt")
            s.add_message("user", "one")
            s.add_message("assistant", "two")
            mgr.save(s)

            path = mgr._get_session_path("fmt")
            lines = path.read_text(encoding="utf-8").strip().split("\n")
            lines_count = len(lines)
            assert lines_count == 3, f"expect save writes JSONL with one metadata row plus two message rows as 3, got {lines_count}"  # 1 metadata + 2 messages

            metadata = json.loads(lines[0])
            assert metadata["_type"] == "metadata", f"expect first JSONL row is metadata marker entry as 'metadata', got {metadata['_type']}"
            assert metadata["key"] == "fmt", f"expect metadata row stores original session key for serialization format as 'fmt', got {metadata['key']}"

            msg1 = json.loads(lines[1])
            assert msg1["role"] == "user", f"expect first message row role is serialized as user in JSONL format as 'user', got {msg1['role']}"
            assert msg1["content"] == "one", f"expect first message row content is serialized as original text in JSONL format as 'one', got {msg1['content']}"

    def test_save_updates_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("k")
            mgr.save(s)
            cached, _ts = mgr._cache["k"]
            assert cached is s, f"expect save updates in-memory cache reference to saved session object as {s}, got {cached}"


class TestSessionManagerLoad:
    def test_load_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            loaded_session = mgr._load("nonexistent")
            assert loaded_session is None, f"expect _load returns None for missing session file, got {loaded_session}"

    def test_load_corrupted_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            path = mgr._get_session_path("bad")
            path.write_text("not valid json\n", encoding="utf-8")
            loaded_session = mgr._load("bad")
            assert loaded_session is None, f"expect _load returns None for corrupted session file content, got {loaded_session}"

    def test_load_preserves_metadata(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("meta")
            s.metadata = {"version": 2}
            s.add_message("user", "x")
            mgr.save(s)

            mgr.invalidate("meta")
            s2 = mgr.get_or_create("meta")
            assert s2.metadata == {"version": 2}, f"expect {{'version': 2}}, got {s2.metadata}"

    def test_load_preserves_created_at(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            s = mgr.get_or_create("ts")
            original_created = s.created_at
            s.add_message("user", "x")
            mgr.save(s)

            mgr.invalidate("ts")
            s2 = mgr.get_or_create("ts")
            observed_created_at = s2.created_at.isoformat()
            expected_created_at = original_created.isoformat()
            assert observed_created_at == expected_created_at, f"expect original_created.isoformat() as {expected_created_at}, got {observed_created_at}"

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
            assert s is not None, f"expect value is not None, got {s}"
            message_count = len(s.messages)
            assert message_count == 1, f"expect loader ignores blank lines and restores one valid message row as 1, got {message_count}"

    def test_load_without_created_at(self):
        """Metadata line without created_at should still load."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            path = mgr._get_session_path("nodate")
            content = json.dumps({"_type": "metadata", "key": "nodate"}) + "\n"
            path.write_text(content, encoding="utf-8")

            s = mgr._load("nodate")
            assert s is not None, f"expect value is not None, got {s}"
            created_at_is_datetime = isinstance(s.created_at, datetime)
            created_at_type = type(s.created_at)
            assert created_at_is_datetime, f"expect loader assigns datetime created_at when metadata is missing created_at as True, got {created_at_type}"


class TestSessionManagerInvalidate:
    def test_invalidate_removes_from_cache(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            mgr.get_or_create("k")
            assert "k" in mgr._cache, f"expect contains 'k', got {mgr._cache}"

            mgr.invalidate("k")
            assert "k" not in mgr._cache, f"expect not contains 'k', got {mgr._cache}"

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

            deleted = mgr.delete("del")
            assert deleted is True, f"expect delete returns True when session file existed and was removed, got {deleted}"
            deleted_session_path_exists = mgr._get_session_path("del").exists()
            assert not deleted_session_path_exists, f"expect delete removes session file from disk as False, got {deleted_session_path_exists}"
            assert "del" not in mgr._cache, f"expect not contains 'del', got {mgr._cache}"

    def test_delete_nonexistent(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            deleted = mgr.delete("nope")
            assert deleted is False, f"expect delete returns False when session key does not exist on disk, got {deleted}"

    def test_delete_cached_only(self):
        """Delete should clear cache even if no file on disk."""
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            mgr.get_or_create("cached_only")
            assert "cached_only" in mgr._cache, f"expect contains 'cached_only', got {mgr._cache}"

            result = mgr.delete("cached_only")
            assert result is False, f"expect delete returns False when only cache entry exists and no file is present, got {result}"  # no file to delete
            assert "cached_only" not in mgr._cache, f"expect not contains 'cached_only', got {mgr._cache}"


class TestSessionManagerListSessions:
    def test_list_empty(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            sessions = mgr.list_sessions()
            assert sessions == [], f"expect list_sessions returns empty list when no session files exist as [], got {sessions}"

    def test_list_multiple(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            for key in ["a:1", "b:2", "c:3"]:
                s = mgr.get_or_create(key)
                s.add_message("user", f"msg-{key}")
                mgr.save(s)

            sessions = mgr.list_sessions()
            session_count = len(sessions)
            assert session_count == 3, f"expect list_sessions returns all three saved session files as 3, got {session_count}"
            keys = [s["key"] for s in sessions]
            key_set = set(keys)
            assert key_set == {"a:1", "b:2", "c:3"}, f"expect {{'a:1', 'b:2', 'c:3'}}, got {key_set}"

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
            assert sessions[0]["key"] == "second", f"expect list_sessions returns most recently updated session first in sorted output as 'second', got {sessions[0]['key']}"  # Most recent first

    def test_list_ignores_non_jsonl_files(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            (Path(tmpdir) / "random.txt").write_text("not a session")

            sessions = mgr.list_sessions()
            assert sessions == [], f"expect list_sessions ignores non-JSONL files in session directory scan as [], got {sessions}"

    def test_list_handles_corrupted_files(self, caplog):
        with tempfile.TemporaryDirectory() as tmpdir:
            mgr = SessionManager(tmpdir)
            (Path(tmpdir) / "bad.jsonl").write_text("{{invalid json")

            # Should not crash, just skip — but the skip must be logged, not silent.
            with caplog.at_level(logging.WARNING):
                sessions = mgr.list_sessions()

            assert sessions == [], f"expect list_sessions skips unreadable session files instead of raising errors as [], got {sessions}"
            has_skip_warning = any("Skipping unreadable session file" in r.message for r in caplog.records)
            assert has_skip_warning, f"expect at least one item matching 'Skipping unreadable session file' in r.message as {True}, got {has_skip_warning} with messages {[r.message for r in caplog.records]}"
