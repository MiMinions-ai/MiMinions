from pathlib import Path

from miminions.session.store import JsonlSessionStore, create_session_id
from miminions.workspace_fs.bootstrap import init_workspace


def test_create_session_id_format():
    session_id = create_session_id()
    assert "_" in session_id, f"Expected session_id to contain '_', but got: {session_id}"
    assert len(session_id.split("_", 1)[1]) == 8, f"Expected session_id to have 8 characters after '_', but got: {session_id}"


def test_jsonl_session_store_append_and_iter(tmp_path: Path):
    init_workspace(tmp_path)
    store = JsonlSessionStore(tmp_path)
    session_id = store.create_session_id()
    
    first = store.append(session_id, "user", "hello")
    second = store.append(session_id, "assistant", "hi there", meta={"source": "test"})

    session_path = store.path_for(session_id)
    assert session_path.exists(), f"Expected session file to exist at {session_path}, but it does not."
    assert session_path.parent == (tmp_path / "sessions"), f"Expected session file to be in {tmp_path / 'sessions'}, but got {session_path.parent}"

    messages = list(store.iter_messages(session_id))
    assert len(messages) == 2, f"Expected 2 messages in the session, but got {len(messages)}"
    assert messages[0]["role"] == "user", f"Expected first message role to be 'user', but got: {messages[0]['role']}"
    assert messages[0]["content"] == "hello", f"Expected first message content to be 'hello', but got: {messages[0]['content']}"
    assert messages[1]["role"] == "assistant", f"Expected second message role to be 'assistant', but got: {messages[1]['role']}"
    assert messages[1]["meta"] == {"source": "test"}, f"Expected second message meta to be {{'source': 'test'}}, but got: {messages[1]['meta']}"
    assert first["session_id"] == session_id, f"Expected first message session_id to be {session_id}, but got: {first['session_id']}"
    assert second["session_id"] == session_id, f"Expected second message session_id to be {session_id}, but got: {second['session_id']}"


def test_jsonl_session_store_missing_session_returns_empty(tmp_path: Path):
    init_workspace(tmp_path)
    store = JsonlSessionStore(tmp_path)
    assert list(store.iter_messages("does-not-exist")) == [], f"Expected iter_messages for non-existent session to return empty list, but got: {list(store.iter_messages('does-not-exist'))}"