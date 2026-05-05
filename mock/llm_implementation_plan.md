# LLM Implementation Plan — Main Branch

## Overview

The goal of this sprint is to wire a live LLM into the MiMinions agent pipeline using
OpenRouter as the provider, and to fully implement every module that touches the LLM
workflow. Nothing is deferred or stubbed — by the end of this plan every layer is
complete: the agent reasons with real tools, the context builder feeds the system
prompt, the distiller extracts real memories using the LLM after every session, the
session store converts history into pydantic_ai message objects for cross-session
memory, and the CLI loop is fully async.

The agent currently runs with `TestModel`, which makes no network calls and simply
echoes tool results. We replace that with `OpenAIModel` pointing at OpenRouter, swap
the internal `get_pydantic_ai_agent()` pattern for a clean `async run()` on Minion,
and wire every supporting module so the full loop works end to end.

---

## Phase 1 — Dependencies & Model Plumbing [COMPLETE]

The first step is installing the OpenAI Python SDK, which pydantic_ai uses as the
transport layer for OpenRouter (OpenRouter speaks the OpenAI wire protocol). We then
replace the default model and redesign the Minion API.

### 1.1  `requirements.txt`
Add `openai>=1.0.0`. Without it, any real LLM call will fail with an import error at
the pydantic_ai transport layer.

### 1.2  `pyproject.toml`
Add `"openai>=1.0.0"` to `[project.dependencies]` so the SDK is installed when the
package is used as a library.

### 1.3  `agent/agent.py` — Model swap
Replace `TestModel` with a real `OpenAIModel` backed by `OpenAIProvider` pointed at
OpenRouter. The model string `openai/gpt-oss-20b:free` is a free-tier model that avoids
burning credits while the system is being proven. The API key is read from
`OPENROUTER_API_KEY` in the environment. Callers who need a different model can still
pass one explicitly to `create_minion(model=...)`.

```python
import os
from pydantic_ai.models.openai import OpenAIModel
from pydantic_ai.providers.openai import OpenAIProvider

# In Minion.__init__, when model=None:
provider = OpenAIProvider(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.environ.get("OPENROUTER_API_KEY", ""),
)
self._model = OpenAIModel("openai/gpt-oss-20b:free", provider=provider)
```

### 1.4  `agent/agent.py` — Replace `get_pydantic_ai_agent()` with `async run()`
The current API forces callers to unwrap the internal pydantic_ai Agent and await it
themselves. That leaks an implementation detail and scatters the LLM call logic across
callers. Instead, Minion becomes the agent — it owns the full reasoning loop and exposes
a single `async run()` that accepts a prompt and optional message history and returns a
plain string. The internal `_pydantic_ai_agent` stays private. After each call, the
full message list is stored on `_last_messages` so the chat loop can hand it back in on
the next turn for within-session multi-turn memory.

```python
async def run(self, prompt: str, message_history=None) -> str:
    self._rebuild_pydantic_ai_agent()
    result = await self._pydantic_ai_agent.run(
        prompt,
        message_history=message_history or None,
    )
    self._last_messages = result.all_messages()
    return result.output
```

### 1.5  `agent/__init__.py`
Update the module docstring example to show `await minion.run(...)` instead of
`get_pydantic_ai_agent()`. Remove `TestModel` from the lazy `__getattr__` exports —
it is no longer the default and should not be advertised as part of the public API.

---

## Phase 2 — Context Builder as System Prompt [COMPLETE]

The ContextBuilder already assembles a rich system prompt string from the workspace's
prompt files (AGENTS.md, USER.md, TOOLS.md, IDENTITY.md), MEMORY.md, global SQLite
insights, the workspace graph summary, and the skills index. The problem is that this
context is currently built in `chat.py` but never actually sent to the LLM — it is
only used internally as context. This phase wires it in as the pydantic_ai system
prompt so it is prepended to every LLM call automatically.

### 2.1  `agent/agent.py` — `set_context()` + `@agent.system_prompt`
Add `set_context(workspace, root_path)` on Minion. When the chat loop calls this before
the first `run()`, the `_rebuild_pydantic_ai_agent()` method will detect that context
is set and register a `@agent.system_prompt` callback. pydantic_ai invokes this callback
before every LLM request and prepends the result as the system message. This means
the agent always sees the full workspace context — prompt files, memory, global insights,
rules — without the chat loop having to manually thread it anywhere.

```python
def set_context(self, workspace: Any, root_path: str | Path) -> None:
    """Attach workspace context so ContextBuilder feeds the system prompt."""
    self._workspace = workspace
    self._root_path = Path(root_path)

# Inside _rebuild_pydantic_ai_agent(), if _workspace and _root_path are set:
_ws = self._workspace
_rp = self._root_path

@agent.system_prompt
def _build_system_prompt() -> str:
    return ContextBuilder().build(_ws, _rp)
```

---

## Phase 3 — Async CLI Chat Loop [COMPLETE]

Real LLM calls are network I/O and must be awaited. The current `chat_command()` is
synchronous and calls a sync `_run_agent()` that returns a placeholder demo reply.
Everything needs to become async. `chat_command()` stays a sync Click entry point but
immediately hands off to an async function via `asyncio.run()`. The Minion is created
once before the loop and lives for the whole session. The loop body is: read input →
`await minion.run()` → print reply. If a previous session is resumed via `--session`,
its JSONL history is loaded and converted to pydantic_ai messages so the LLM has
context from the prior conversation (via the session store changes in Phase 4.3).

### 3.1  `interface/cli/chat.py` — Full async rewrite
The complete rewrite removes `_default_agent_reply()`, `_run_agent()`, and
`_default_memory_llm_filter()`. In their place:

- `asyncio.run(_chat_loop(...))` is called from the sync Click command.
- The Minion is built once with `create_minion()`, then `set_context()` is called
  immediately to wire the workspace context into the system prompt.
- If `--session` was passed to the CLI, the store's new `load_as_pydantic_messages()`
  method (Phase 4.3) is called to seed `message_history` with the prior conversation.
- The `while True` loop reads input, saves it to the JSONL store, calls
  `await minion.run(user_text, message_history=message_history)`, saves the reply,
  and updates `message_history = minion._last_messages`.
- All LLM errors (rate limits, timeouts, network failures) are caught per-turn and
  surfaced as a readable error line so one failure does not crash the session.
- The `_run_session_distillation()` call in the `finally` block runs the real
  LLM-backed distiller (Phase 4.1) so memory is written after every session.
- The real `llm_filter` callable from Phase 4.1 is passed directly to
  `MemoryDistiller`, replacing the empty placeholder.

```python
def chat_command(workspace_ref, session_id):
    """Start an interactive async chat session for a workspace."""
    asyncio.run(_chat_loop(workspace_ref, session_id))

async def _chat_loop(workspace_ref, session_id):
    manager = WorkspaceManager(get_config_dir())
    workspace = _resolve_workspace(manager, workspace_ref)
    root = Path(workspace.root_path)
    store = JsonlSessionStore(root)

    if not session_id:
        session_id = store.create_session_id()

    # Load prior history if resuming a session.
    message_history = store.load_as_pydantic_messages(session_id)

    minion = create_minion(name="MiMinions", description="MiMinions AI agent")
    minion.set_context(workspace, root)
    # Register tools ...

    try:
        while True:
            user_text = input("> ").strip()
            if not user_text or user_text.lower() in {"exit", "quit"}:
                break
            store.append(session_id, "user", user_text)
            try:
                reply = await minion.run(user_text, message_history=message_history)
                message_history = minion._last_messages
            except Exception as exc:
                reply = f"[error] {type(exc).__name__}: {exc}"
            store.append(session_id, "assistant", reply)
            print(f"\n{reply}\n")
    finally:
        _run_session_distillation(workspace, root, session_id)
```

---

## Phase 4 — Full Module Implementations [COMPLETE]

This phase completes the three modules from `llm_issue.txt` that require real
implementations: the `llm_filter` callable for post-session memory extraction, the
session store's pydantic_ai message conversion, and verifying the context builder is
correctly wired (no code changes needed there, only the wiring from Phase 2).

### 4.1  `memory/distiller.py` — Real `llm_filter` implementation

The `MemoryDistiller` class is already fully built and calls `llm_filter(transcript, ...)`
to extract structured data from a session transcript. What is missing is the actual
`llm_filter` implementation — currently `chat.py` passes a placeholder that returns
empty fields, so the distiller runs but stores nothing.

We implement `create_llm_filter(model)` as a factory function in `memory/distiller.py`.
It accepts an `OpenAIModel` (or any pydantic_ai model) and returns a synchronous
callable that matches the `Callable[..., dict[str, Any]]` signature that `MemoryDistiller`
expects. The callable sends the compacted session transcript to the LLM with a strict
structured extraction prompt, then parses the JSON response into `history_summary`,
`workspace_facts`, and `global_insights`.

The function must be synchronous because `MemoryDistiller.distill_session()` is
synchronous (it's called from a `finally` block). The LLM call is made synchronously
using the httpx client underlying the openai SDK, or by running an event loop inline
with `asyncio.get_event_loop().run_until_complete()` for the async pydantic_ai path.

```python
EXTRACTION_PROMPT = """
You are a memory extraction system. Read the conversation transcript below and extract
the following, responding ONLY with valid JSON — no markdown, no explanation:

{
  "history_summary": "<one or two sentences summarising what happened in this session>",
  "workspace_facts": ["<concrete fact about the project or workspace>", ...],
  "global_insights": ["<general insight that applies across workspaces>", ...]
}

Rules:
- history_summary must not be empty.
- workspace_facts are project-specific: file names, decisions, bugs, features.
- global_insights are reusable patterns: best practices, user preferences, recurring issues.
- Return empty lists if there is nothing to extract.
- Respond with JSON only.

Transcript:
{transcript}
"""

def create_llm_filter(model: Any) -> Callable[..., dict[str, Any]]:
    """Factory: returns a real LLM-backed llm_filter callable for MemoryDistiller.

    The returned function is synchronous so it can be used inside the sync
    distill_session() pipeline.
    """
    def llm_filter(transcript: str, **_kwargs: Any) -> dict[str, Any]:
        if not transcript.strip():
            return {"history_summary": "", "workspace_facts": [], "global_insights": []}

        prompt = EXTRACTION_PROMPT.format(transcript=transcript)

        # Run the async pydantic_ai call synchronously.
        extraction_agent = Agent(model=model, instructions="Extract memory from transcripts.")
        result = asyncio.get_event_loop().run_until_complete(
            extraction_agent.run(prompt)
        )
        raw = result.output.strip()

        # Strip markdown fences if the model wraps its JSON.
        if raw.startswith("```"):
            raw = "\n".join(
                line for line in raw.splitlines()
                if not line.strip().startswith("```")
            )

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            return {"history_summary": raw[:500], "workspace_facts": [], "global_insights": []}

        return {
            "history_summary": str(payload.get("history_summary", "")).strip(),
            "workspace_facts": payload.get("workspace_facts", []),
            "global_insights": payload.get("global_insights", []),
        }

    return llm_filter
```

In `chat.py`, the real filter is created at the start of `_run_session_distillation()`
by calling `create_llm_filter(minion._model)` and passing it to `MemoryDistiller`.

### 4.2  `agent/context_builder.py` — no code changes
The ContextBuilder is already fully implemented. It reads all workspace files, injects
global SQLite insights, formats the workspace graph, and returns a complete context
string. The only work in this phase is the wiring done in Phase 2 via `set_context()`.
No edits to `context_builder.py` itself.

### 4.3  `session/store.py` — `load_as_pydantic_messages()`
The session store currently only writes and reads raw JSONL dicts. pydantic_ai's
`message_history` parameter requires a `list[ModelMessage]` — specifically a mix of
`ModelRequest` (for user/system turns) and `ModelResponse` (for assistant turns). We
add a method that loads the JSONL for a given session and converts each record into the
correct pydantic_ai message type. This gives the LLM full persistent memory across
sessions when the user passes `--session <id>` to the CLI.

The conversion maps:
- `role == "user"` → `ModelRequest(parts=[UserPromptPart(content=...)])`
- `role == "assistant"` → `ModelResponse(parts=[TextPart(content=...)], model_name="openrouter")`
- Any other role → skipped (tool results are not re-injected from JSONL).

```python
def load_as_pydantic_messages(self, session_id: str) -> list:
    """Load a saved session as pydantic_ai ModelMessage objects.

    Returns an empty list if the session does not exist or is empty.
    This allows a resumed session to pass prior history into minion.run()
    so the LLM has full context from the previous conversation.
    """
    from pydantic_ai.messages import (
        ModelRequest, ModelResponse,
        UserPromptPart, TextPart,
    )

    messages = []
    for record in self.iter_messages(session_id):
        role = record.get("role", "")
        content = record.get("content", "")
        if not content:
            continue
        if role == "user":
            messages.append(
                ModelRequest(parts=[UserPromptPart(content=content)])
            )
        elif role == "assistant":
            messages.append(
                ModelResponse(
                    parts=[TextPart(content=content)],
                    model_name="openrouter",
                )
            )
    return messages
```

---

## Phase 5 — Example Chat Test Script [COMPLETE]

Rather than requiring the user to set up a workspace through the CLI before they can
test anything, we create a fully self-contained test script in `examples/example_chat/`.
This script is a direct substitute for the full CLI — it manages its own workspace
lifecycle, creates all required files on first run, opens the existing workspace on
subsequent runs, runs the full async chat loop with the real Minion and real tools, and
runs post-session distillation. The generated workspace files are gitignored so only
the Python script is tracked.

### 5.1  `examples/example_chat/chat_example.py`

**First run** — bootstraps the workspace:
- Creates `_workspace/prompt/AGENTS.md` with a seed identity prompt describing MiMinions.
- Creates `_workspace/prompt/USER.md` with a placeholder user preferences section.
- Creates `_workspace/memory/MEMORY.md` with an empty structure (will be filled by distiller).
- Creates `_workspace/sessions/` and `_workspace/data/` directories.
- Saves `_workspace/workspace.json` with a `Workspace` object so ContextBuilder and the
  session store can find everything they need.

**Subsequent runs** — detects `_workspace/workspace.json` and opens it, preserving all
memory and session history from previous runs.

**Chat loop** — uses the real `create_minion()`, calls `set_context()`, registers demo
tools, and enters the same `await minion.run()` loop used by the CLI. On exit, calls
`MemoryDistiller` with the real `create_llm_filter()` so memory accumulates across runs.

**Session resumption** — if `--session <id>` is passed on the command line, loads the
prior JSONL via `store.load_as_pydantic_messages()` and passes it in as `message_history`
on the first call.

```
examples/
  example_chat/
    chat_example.py   ← tracked by git
    .gitignore        ← ignores _workspace/
    _workspace/       ← generated at runtime, NOT tracked
      prompt/
        AGENTS.md
        USER.md
      memory/
        MEMORY.md
      sessions/
      data/
      workspace.json
```

### 5.2  `examples/example_chat/.gitignore`
```
_workspace/
```

---

## Phase 6 — Demo Tools & Final Verification [COMPLETE]

Before the implementation is complete, we verify that every layer works together in the
example script: the model connects to OpenRouter, tools are called correctly, the
system prompt contains the ContextBuilder output, sessions are persisted, and the
distiller writes memory after the session.

### 6.1  Demo tools registered in `chat_example.py`
Two simple tools are registered on the Minion to prove the full model → tool → reply
cycle works:

- `add_numbers(a: int, b: int) -> int` — the simplest possible proof of tool calling.
  Asking "what is 3 + 7?" should cause the LLM to emit a tool call, receive the result
  `10`, and return a natural language reply.
- `list_tools() -> list[str]` — calls `minion.list_tools()` and returns the registered
  tool names. Asking "what tools do you have?" should trigger this and list them.

### 6.2  Full verification checklist
- [ ] `pip install openai` succeeds (or `pip install -e .` installs it).
- [ ] `chat_example.py` runs without errors on first run and creates `_workspace/`.
- [ ] The printed context header shows workspace name and session ID.
- [ ] Asking "add 3 and 7" triggers a tool call to `add_numbers` and the reply contains `10`.
- [ ] Asking "what tools do you have?" triggers `list_tools` and lists both tools.
- [ ] Multi-turn context works: referring back to something said earlier gets a correct answer.
- [ ] `_workspace/sessions/<session_id>.jsonl` exists and contains all user + assistant turns.
- [ ] After exit, the distiller runs and the LLM extraction prompt is sent to OpenRouter.
- [ ] `_workspace/memory/MEMORY.md` is updated if the session contained extractable facts.
- [ ] Running `chat_example.py` again (same or new session) reopens the workspace correctly.
- [ ] Passing `--session <previous_id>` resumes the prior conversation with full context.
- [ ] The CLI `chat start --workspace <name>` works identically to the example script.

---

## Phase 7 — Workflow Modularization [COMPLETE]

To keep the codebase cleanly separated by concern, we need to restructure the folders into
`agent`, `memory`, and `context`, ensuring each module only contains its relevant logic.

### 7.1  Split out `context` folder
- Create `src/miminions/context/` directory with an `__init__.py`.
- Move `src/miminions/agent/context_builder.py` to `src/miminions/context/context_builder.py`.
- Update all imports across the codebase that referenced `miminions.agent.context_builder`
  to point to `miminions.context.context_builder` (e.g., in `agent.py`, `chat.py`, `agent/__init__.py`).

### 7.2  Extract `llm_filter` into its own file
- Create `src/miminions/memory/llm_filter.py`.
- Put the `create_llm_filter(model)` implementation (from Phase 4.1) and the `EXTRACTION_PROMPT`
  into this new file instead of cluttering `distiller.py`.
- Update imports in `chat.py` to import `create_llm_filter` from `miminions.memory.llm_filter`.

### 7.3  Split `agent/models.py` by domain
Currently `agent/models.py` couples agent configuration with tool and memory types. We will split this:
- Create `src/miminions/tools/models.py` and move `ToolParameter`, `ToolSchema`, `ToolDefinition`, `ToolExecutionRequest`, `ExecutionStatus`, `ToolExecutionResult`, and `ParameterType` there.
- Create `src/miminions/memory/models.py` and move `MemoryEntry` and `MemoryQueryResult` there.
- Keep only `AgentConfig` and `AgentState` in `src/miminions/agent/models.py`.
- Update all references to these models across the codebase (e.g., `agent.py`, `tools/generic.py`, `memory/base_memory.py`).

### 7.4  Cleanup documentation
- Delete `src/miminions/agent/QUICKSTART.md`.
- Ensure each of the core folders (`agent`, `memory`, `context`) contains exactly one
  `README.md` file describing its purpose, and no other markdown files.

---

## Files Summary

| File | Action | Phase |
|------|--------|-------|
| `requirements.txt` | add `openai>=1.0.0` | 1.1 |
| `pyproject.toml` | add `"openai>=1.0.0"` to dependencies | 1.2 |
| `agent/agent.py` | model swap + `async run()` + `set_context()`, fix imports | 1.3, 1.4, 2.1, 7.1 |
| `agent/__init__.py` | update docstring + remove TestModel export, fix imports | 1.5, 7.1 |
| `interface/cli/chat.py` | full async rewrite, wire real llm_filter, fix imports | 3.1, 7.1, 7.2 |
| `memory/llm_filter.py` | **NEW** — add `create_llm_filter()` factory + prompt | 4.1, 7.2 |
| `session/store.py` | add `load_as_pydantic_messages()` | 4.3 |
| `context/context_builder.py` | **MOVED** — moved from `agent/` | 7.1 |
| `context/__init__.py` | **NEW** — init exports | 7.1 |
| `context/README.md` | **NEW** — documentation for context package | 7.4 |
| `agent/models.py` | **MODIFIED** — remove tool and memory models | 7.3 |
| `tools/models.py` | **NEW** — extract tool execution models | 7.3 |
| `memory/models.py` | **NEW** — extract memory entry models | 7.3 |
| `agent/QUICKSTART.md` | **DELETE** — remove quickstart | 7.4 |
| `examples/example_chat/chat_example.py` | **NEW** — full standalone test harness | 5.1 |
| `examples/example_chat/.gitignore` | **NEW** — ignore `_workspace/` | 5.2 |

## Files NOT changed
- `memory/distiller.py` — already fully implemented (logic kept, `llm_filter` externalized).
- `memory/sqlite.py` — `get_global_memory_db_path()` already in place.
- `memory/md_store.py` — already implemented.
