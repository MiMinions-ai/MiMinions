"""Unit tests for gateway.events module."""
from datetime import datetime

from miminions.core.gateway.events import InboundMessage, OutboundMessage


class TestInboundMessage:
    """Tests for InboundMessage dataclass."""

    def test_creation_required_fields(self):
        """Test InboundMessage with only required fields."""
        msg = InboundMessage(
            channel="telegram",
            sender_id="user1",
            chat_id="chat1",
            content="hello",
        )
        assert msg.channel == "telegram", f"expect InboundMessage preserves required channel field from constructor input as 'telegram', got {msg.channel}"
        assert msg.sender_id == "user1", f"expect InboundMessage preserves required sender_id field from constructor input as 'user1', got {msg.sender_id}"
        assert msg.chat_id == "chat1", f"expect InboundMessage preserves required chat_id field from constructor input as 'chat1', got {msg.chat_id}"
        assert msg.content == "hello", f"expect InboundMessage preserves required content field from constructor input as 'hello', got {msg.content}"

    def test_defaults(self):
        """Test default values are correctly initialized."""
        msg = InboundMessage(
            channel="test", sender_id="u", chat_id="c", content="hi"
        )
        timestamp_is_datetime = isinstance(msg.timestamp, datetime)
        timestamp_type = type(msg.timestamp)
        assert timestamp_is_datetime, f"expect inbound message timestamp to be datetime as True, got {timestamp_type}"
        assert msg.media == [], f"expect InboundMessage default media list is empty when not provided as [], got {msg.media}"
        assert msg.metadata == {}, f"expect InboundMessage default metadata mapping is empty when not provided as {{}}, got {msg.metadata}"
        assert msg.session_key_override is None, f"expect InboundMessage session_key_override defaults to None when omitted, got {msg.session_key_override}"

    def test_media_and_metadata(self):
        """Test optional fields."""
        msg = InboundMessage(
            channel="discord",
            sender_id="u2",
            chat_id="c2",
            content="image",
            media=["https://example.com/img.png"],
            metadata={"thread_id": "t1"},
        )
        assert msg.media == ["https://example.com/img.png"], f"expect InboundMessage preserves provided media list in payload as ['https://example.com/img.png'], got {msg.media}"
        assert msg.metadata == {"thread_id": "t1"}, f"expect InboundMessage preserves provided metadata mapping in payload as {'thread_id': 't1'}, got {msg.metadata}"

    def test_session_key_default(self):
        """Test session_key property defaults to channel:chat_id."""
        msg = InboundMessage(
            channel="slack", sender_id="u", chat_id="C01234", content=""
        )
        assert msg.session_key == "slack:C01234", f"expect session_key derives from channel and chat_id when no override is provided as 'slack:C01234', got {msg.session_key}"

    def test_session_key_override(self):
        """Test session_key respects session_key_override."""
        msg = InboundMessage(
            channel="slack",
            sender_id="u",
            chat_id="C01234",
            content="",
            session_key_override="slack:C01234:thread-99",
        )
        assert msg.session_key == "slack:C01234:thread-99", f"expect session_key property respects explicit session_key_override value as 'slack:C01234:thread-99', got {msg.session_key}"

    def test_mutable_defaults_are_independent(self):
        """Test that mutable defaults (media, metadata) are not shared."""
        msg1 = InboundMessage(channel="a", sender_id="u", chat_id="c", content="")
        msg2 = InboundMessage(channel="b", sender_id="u", chat_id="c", content="")
        msg1.media.append("x")
        msg1.metadata["k"] = "v"
        assert msg2.media == [], f"expect mutable default media list is not shared across InboundMessage instances as [], got {msg2.media}"
        assert msg2.metadata == {}, f"expect mutable default metadata mapping is not shared across InboundMessage instances as {{}}, got {msg2.metadata}"


class TestOutboundMessage:
    """Tests for OutboundMessage dataclass."""

    def test_creation_required_fields(self):
        """Test OutboundMessage with required fields."""
        msg = OutboundMessage(channel="telegram", chat_id="c1", content="reply")
        assert msg.channel == "telegram", f"expect OutboundMessage preserves required channel field from constructor input as 'telegram', got {msg.channel}"
        assert msg.chat_id == "c1", f"expect OutboundMessage preserves required chat_id field from constructor input as 'c1', got {msg.chat_id}"
        assert msg.content == "reply", f"expect OutboundMessage preserves required content field from constructor input as 'reply', got {msg.content}"

    def test_defaults(self):
        """Test default values."""
        msg = OutboundMessage(channel="test", chat_id="c", content="hi")
        assert msg.reply_to is None, f"expect OutboundMessage reply_to defaults to None when omitted, got {msg.reply_to}"
        assert msg.media == [], f"expect OutboundMessage default media list is empty when not provided as [], got {msg.media}"
        assert msg.metadata == {}, f"expect OutboundMessage default metadata mapping is empty when not provided as {{}}, got {msg.metadata}"

    def test_reply_to(self):
        """Test reply_to field."""
        msg = OutboundMessage(
            channel="discord", chat_id="c", content="ok", reply_to="msg-42"
        )
        assert msg.reply_to == "msg-42", f"expect OutboundMessage preserves reply_to threading id when provided as 'msg-42', got {msg.reply_to}"

    def test_media_and_metadata(self):
        """Test optional fields."""
        msg = OutboundMessage(
            channel="whatsapp",
            chat_id="c",
            content="",
            media=["file.pdf"],
            metadata={"caption": "doc"},
        )
        assert msg.media == ["file.pdf"], f"expect OutboundMessage preserves provided media list in payload as ['file.pdf'], got {msg.media}"
        assert msg.metadata == {"caption": "doc"}, f"expect OutboundMessage preserves provided metadata mapping in payload as {'caption': 'doc'}, got {msg.metadata}"

    def test_mutable_defaults_are_independent(self):
        """Test that mutable defaults are not shared."""
        m1 = OutboundMessage(channel="a", chat_id="c", content="")
        m2 = OutboundMessage(channel="b", chat_id="c", content="")
        m1.media.append("y")
        assert m2.media == [], f"expect mutable default media list is not shared across OutboundMessage instances as [], got {m2.media}"
