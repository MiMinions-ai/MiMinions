from pathlib import Path

from miminions.session.store import JsonlSessionStore, create_session_id
from miminions.workspace_fs.bootstrap import init_workspace


def test_create_session_id_format():
    session_id = create_session_id()
    assert "_" in session_id
    assert len(session_id.split("_", 1)[1]) == 8


def test_jsonl_session_store_append_and_iter(tmp_path: Path):
    init_workspace(tmp_path)
    store = JsonlSessionStore(tmp_path)
    session_id = store.create_session_id()
    
    first = store.append(session_id, "user", "hello")
    second = store.append(session_id, "assistant", "hi there", meta={"source": "test"})

    session_path = store.path_for(session_id)
    assert session_path.exists()
    assert session_path.parent == (tmp_path / "sessions")

    messages = list(store.iter_messages(session_id))
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[0]["content"] == "hello"
    assert messages[1]["role"] == "assistant"
    assert messages[1]["meta"] == {"source": "test"}
    assert first["session_id"] == session_id
    assert second["session_id"] == session_id


def test_jsonl_session_store_missing_session_returns_empty(tmp_path: Path):
    init_workspace(tmp_path)
    store = JsonlSessionStore(tmp_path)
    assert list(store.iter_messages("does-not-exist")) == []