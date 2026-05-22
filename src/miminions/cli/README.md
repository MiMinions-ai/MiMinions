# MiMinions CLI & Chat Interface

The `interface/cli/` module contains the interactive command-line entry points for MiMinions.

## Features

- **Async Chat Loop**: The `chat` command drops you into a fully asynchronous reasoning loop with the agent, persisting logs to `_workspace/sessions/`.
- **Session Resumption**: By passing `--session <session_id>` to `chat start`, the CLI automatically loads the `.jsonl` transcript of that session from `JsonlSessionStore`. It converts the history back into native `pydantic_ai` messages, meaning the LLM regains complete conversational context from previous runs.
- **Background Distillation**: When you type `exit` or close the chat, the CLI triggers the `MemoryDistiller` automatically in the background, making sure memory is extracted without forcing you to wait.
