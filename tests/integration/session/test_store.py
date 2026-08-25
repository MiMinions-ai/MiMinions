from pathlib import Path

from pydantic_ai.messages import (
    ModelRequest,
    ModelResponse,
    TextPart,
    ToolCallPart,
    ToolReturnPart,
    UserPromptPart,
)

from miminions.session.store import (
    JsonlSessionStore,
    create_session_id,
    trim_message_history,
)
from miminions.workspace_fs.bootstrap import init_workspace


def _user(content: str) -> ModelRequest:
    return ModelRequest(parts=[UserPromptPart(content=content)])


def _assistant(content: str) -> ModelResponse:
    return ModelResponse(parts=[TextPart(content=content)])


def _tool_call() -> ModelResponse:
    return ModelResponse(parts=[ToolCallPart(tool_name="t", args={}, tool_call_id="c1")])


def _tool_return() -> ModelRequest:
    return ModelRequest(parts=[ToolReturnPart(tool_name="t", content="r", tool_call_id="c1")])


def test_create_session_id_format():
    session_id = create_session_id()
    assert "_" in session_id, f"expect create_session_id includes underscore separator between timestamp and random suffix as '_', got {session_id}"
    session_suffix = session_id.split("_", 1)[1]
    suffix_length = len(session_suffix)
    assert suffix_length == 8, f"expect create_session_id random suffix length is exactly 8 characters, got {suffix_length}"


def test_jsonl_session_store_append_and_iter(tmp_path: Path):
    init_workspace(tmp_path)
    store = JsonlSessionStore(tmp_path)
    session_id = store.create_session_id()
    
    first = store.append(session_id, "user", "hello")
    second = store.append(session_id, "assistant", "hi there", meta={"source": "test"})

    session_path = store.path_for(session_id)
    session_file_exists = session_path.exists()
    assert session_file_exists, f"expect append creates session jsonl file as True, got {session_file_exists}"
    assert session_path.parent == (tmp_path / "sessions"), f"expect tmp_path / 'sessions', got {session_path.parent}"

    messages = list(store.iter_messages(session_id))
    message_count = len(messages)
    assert message_count == 2, f"expect iter_messages returns both appended user and assistant records as 2, got {message_count}"
    assert messages[0]["role"] == "user", f"expect first iterated session record role is user as 'user', got {messages[0]['role']}"
    assert messages[0]["content"] == "hello", f"expect first iterated session record content matches appended user text as 'hello', got {messages[0]['content']}"
    assert messages[1]["role"] == "assistant", f"expect second iterated session record role is assistant as 'assistant', got {messages[1]['role']}"
    assert messages[1]["meta"] == {"source": "test"}, f"expect assistant record metadata keeps appended source field as {'source': 'test'}, got {messages[1]['meta']}"
    assert first["session_id"] == session_id, f"expect append return payload carries original session_id for first append call as {session_id}, got {first['session_id']}"
    assert second["session_id"] == session_id, f"expect append return payload carries original session_id for second append call as {session_id}, got {second['session_id']}"


def test_jsonl_session_store_missing_session_returns_empty(tmp_path: Path):
    init_workspace(tmp_path)
    store = JsonlSessionStore(tmp_path)
    messages = list(store.iter_messages("does-not-exist"))
    assert messages == [], f"expect iter_messages returns empty list for missing session id as [], got {messages}"


def test_trim_under_limit_returns_history_unchanged():
    messages = [_user("u1"), _assistant("a1")]
    trimmed = trim_message_history(messages, max_messages=40)
    assert trimmed is messages, f"expect trim_message_history returns original history object when message count is under limit as {messages}, got {trimmed}"


def test_trim_cuts_at_a_user_turn_boundary():
    messages = []
    for i in range(30):
        messages.append(_user(f"u{i}"))
        messages.append(_assistant(f"a{i}"))

    trimmed = trim_message_history(messages, max_messages=40)

    trimmed_count = len(trimmed)
    assert trimmed_count <= 40, f"expect len(trimmed) <= 40, got {trimmed_count}"
    first = trimmed[0]
    first_is_model_request = isinstance(first, ModelRequest)
    first_type = type(first)
    assert first_is_model_request, f"expect trimmed history starts with ModelRequest as {True}, got {first_is_model_request} with first type {first_type}"
    has_user_prompt_part = any(isinstance(part, UserPromptPart) for part in first.parts)
    assert has_user_prompt_part, f"expect trimmed first ModelRequest contains at least one UserPromptPart as {True}, got {has_user_prompt_part} with parts {first.parts}"


def test_trim_never_starts_mid_tool_exchange():
    messages = [
        _user("u1"), _tool_call(), _tool_return(), _assistant("a1"),
        _user("u2"), _tool_call(), _tool_return(), _assistant("a2"),
    ]

    # A naive messages[-6:] slice would start at the tool-return request;
    # the trim must skip forward to the next user turn instead.
    trimmed = trim_message_history(messages, max_messages=6)

    assert trimmed[0] is messages[4], f"expect trim starts from next user turn boundary instead of mid tool exchange as {messages[4]}, got {trimmed[0]}"
    trimmed_count = len(trimmed)
    assert trimmed_count == 4, f"expect trimmed history contains one complete user-tool-assistant exchange after boundary cut as 4, got {trimmed_count}"


def test_trim_without_user_boundary_returns_history_unchanged():
    messages = [_assistant(f"a{i}") for i in range(10)]
    trimmed = trim_message_history(messages, max_messages=4)
    assert trimmed is messages, f"expect trim_message_history returns original history when no user-turn boundary exists in tail window as {messages}, got {trimmed}"
