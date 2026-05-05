# Chat Example Test Harness

This directory contains `chat_example.py`, a fully self-contained standalone test script.

## How it works
Rather than requiring you to use the CLI to bootstrap a global workspace, `chat_example.py` creates a temporary, local `_workspace` directory directly inside this folder. 

When you run it:
1. **Bootstrapping**: It creates the local `_workspace` directory with default identity prompts (`AGENTS.md`, `USER.md`) and an empty `MEMORY.md`.
2. **Setup**: It instantiates the `Minion`, applies the local workspace via `set_context()`, and registers two simple demo tools (`add_numbers`, `list_tools`).
3. **Execution**: It drops you into the same async chat loop used by the main CLI, allowing you to converse with the agent.
4. **Resumption**: You can pass `--session <id>` to resume previous chat logs from `_workspace/sessions/`.
5. **Distillation**: When you type `exit`, it triggers the background `MemoryDistiller`, using the LLM to write any facts it learned into the local `_workspace`.

Because `_workspace/` is gitignored, this serves as a completely safe sandbox to test prompt changes, tool execution, and the full memory pipeline end-to-end!
