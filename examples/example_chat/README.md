# Chat Example Test Harness

This directory contains `chat_example.py`, a self-contained standalone chat harness.

## How it works

The architecture in `chat_example.py` demonstrates the same core agent lifecycle as the
CLI chat implementation, but uses a local workspace and direct `Minion.run()` calls
instead of the CLI task-dispatch and global configuration machinery.

When you run it, it executes the identical 5-step agent lifecycle:

1. **Workspace Initialization**: It calls `init_workspace(root)` (from `miminions.core.workspace.bootstrap`) to automatically scaffold a local `_workspace` folder with `prompt/`, `memory/`, and `skills/` directories, completely identical to running `miminions workspace init-files` in the CLI.
2. **Context Injection**: It instantiates the `Minion` and calls `minion.set_context()`. This internally hooks up the core `ContextBuilder` to ingest the generated markdown files and inject them into the LLM's system prompt.
3. **Session Store & History**: It utilizes `JsonlSessionStore` to store chat transcripts. If resuming (`--session <id>`), it parses previous messages as Pydantic AI messages to give the LLM full history context.
4. **Agent Run Loop**: It enters a standard `while True` loop to accept user input, calling `await minion.run(user_text, message_history)` exactly like the CLI.
5. **Memory Distillation**: On exit, it safely triggers the exact same background `MemoryDistiller` logic used in production to analyze the transcript and extract Tier 1 (History), Tier 2 (Facts), and Tier 3 (Insights) back into the local `_workspace`.

Because the local `_workspace/` directory is gitignored, this serves as a completely safe sandbox to test prompt changes, tool execution, and the full memory pipeline end-to-end, guaranteeing that any behavior you verify here will translate seamlessly to the main agent.
