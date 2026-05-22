from miminions.session.store import JsonlSessionStore


def append_transcript(root, session_id: str = "s1") -> str:
    """Append a minimal two-turn transcript to a session store and return the session id."""
    store = JsonlSessionStore(root)
    store.append(session_id, "user", "Please enforce black formatting in this repo")
    store.append(session_id, "assistant", "Will do. I will keep formatting deterministic.")
    return session_id
