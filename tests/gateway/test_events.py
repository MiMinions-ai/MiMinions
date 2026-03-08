"""Unit tests for gateway.events module."""
import pytest
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
        assert msg.channel == "telegram"
        assert msg.sender_id == "user1"
        assert msg.chat_id == "chat1"
        assert msg.content == "hello"

    def test_defaults(self):
        """Test default values are correctly initialized."""
        msg = InboundMessage(
            channel="test", sender_id="u", chat_id="c", content="hi"
        )
        assert isinstance(msg.timestamp, datetime)
        assert msg.media == []
        assert msg.metadata == {}
        assert msg.session_key_override is None

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
        assert msg.media == ["https://example.com/img.png"]
        assert msg.metadata == {"thread_id": "t1"}

    def test_session_key_default(self):
        """Test session_key property defaults to channel:chat_id."""
        msg = InboundMessage(
            channel="slack", sender_id="u", chat_id="C01234", content=""
        )
        assert msg.session_key == "slack:C01234"

    def test_session_key_override(self):
        """Test session_key respects session_key_override."""
        msg = InboundMessage(
            channel="slack",
            sender_id="u",
            chat_id="C01234",
            content="",
            session_key_override="slack:C01234:thread-99",
        )
        assert msg.session_key == "slack:C01234:thread-99"

    def test_mutable_defaults_are_independent(self):
        """Test that mutable defaults (media, metadata) are not shared."""
        msg1 = InboundMessage(channel="a", sender_id="u", chat_id="c", content="")
        msg2 = InboundMessage(channel="b", sender_id="u", chat_id="c", content="")
        msg1.media.append("x")
        msg1.metadata["k"] = "v"
        assert msg2.media == []
        assert msg2.metadata == {}


class TestOutboundMessage:
    """Tests for OutboundMessage dataclass."""

    def test_creation_required_fields(self):
        """Test OutboundMessage with required fields."""
        msg = OutboundMessage(channel="telegram", chat_id="c1", content="reply")
        assert msg.channel == "telegram"
        assert msg.chat_id == "c1"
        assert msg.content == "reply"

    def test_defaults(self):
        """Test default values."""
        msg = OutboundMessage(channel="test", chat_id="c", content="hi")
        assert msg.reply_to is None
        assert msg.media == []
        assert msg.metadata == {}

    def test_reply_to(self):
        """Test reply_to field."""
        msg = OutboundMessage(
            channel="discord", chat_id="c", content="ok", reply_to="msg-42"
        )
        assert msg.reply_to == "msg-42"

    def test_media_and_metadata(self):
        """Test optional fields."""
        msg = OutboundMessage(
            channel="whatsapp",
            chat_id="c",
            content="",
            media=["file.pdf"],
            metadata={"caption": "doc"},
        )
        assert msg.media == ["file.pdf"]
        assert msg.metadata == {"caption": "doc"}

    def test_mutable_defaults_are_independent(self):
        """Test that mutable defaults are not shared."""
        m1 = OutboundMessage(channel="a", chat_id="c", content="")
        m2 = OutboundMessage(channel="b", chat_id="c", content="")
        m1.media.append("y")
        assert m2.media == []
