# MiMinions

An agentic framework built on [pydantic-ai](https://ai.pydantic.dev/) with
[Model Context Protocol](https://modelcontextprotocol.io/) (MCP) server support,
a generic tool system, three-tier memory, and local-first workspaces.

📖 **Full documentation: [miminions.ai](https://miminions.ai)**

## Features

- **Minion agent** — an async, LLM-powered agent on `pydantic-ai`, defaulting to
  [OpenRouter](https://openrouter.ai/) (with OpenAI, Anthropic, Gemini, and an
  offline test model also selectable), with streaming replies, retries,
  request timeouts, and observability hooks.
- **Generic tool system** — turn a typed Python function into an agent-callable
  tool with an auto-derived JSON schema; no boilerplate.
- **MCP integration** — connect to MCP servers and load their tools alongside
  your own functions.
- **Three-tier memory** — a chronological session log (`HISTORY.md`), stable
  workspace facts (`MEMORY.md`), and a cross-workspace SQLite vector store, with
  an LLM distiller that promotes insights across tiers.
- **Vector memory** — `SQLiteMemory` with semantic, keyword, full-text,
  metadata, regex, hybrid, and date-range search, embeddings via
  [fastembed](https://github.com/qdrant/fastembed) (ONNX — no PyTorch/CUDA).
- **Workspaces** — a node/rule graph plus an on-disk layout (`prompt/`,
  `memory/`, `skills/`, `sessions/`, `data/`) that drives each agent's context.
- **CLI** — manage agents, tasks, knowledge, workspaces, and an interactive chat
  from the `miminions` command; state persists under `~/.miminions/` by default
  and can be relocated with `MIMINIONS_HOME`.
- **Local data manager** — content-addressable (SHA-256) storage with
  deduplication, a master index, and an append-only transaction log.
- **Async-first** — full asynchronous operation throughout.

## Installation

```bash
pip install miminions
```

Or with [uv](https://docs.astral.sh/uv/):

```bash
uv add miminions
```

Requires **Python 3.12+**. SQLite vector memory is an optional extra (it adds
`fastembed`, `sqlite-vec`, and `pysqlite3`):

```bash
pip install miminions[sqlite]   # or miminions[all]
```

The agent uses OpenRouter by default — set your key before running:

```bash
export OPENROUTER_API_KEY="sk-or-..."
```

MiMinions stores local CLI/workspace state in `~/.miminions` by default. Set
`MIMINIONS_HOME` to use a different location:

```bash
export MIMINIONS_HOME="/path/to/miminions-home"
```

## Quick Start

### A first agent with a custom tool

```python
import asyncio
from miminions.agent import create_minion

async def main():
    agent = create_minion("MyAgent")

    def add(a: int, b: int) -> int:
        return a + b

    agent.register_tool("add", "Add two numbers", add)

    # The model decides when to call the tool.
    reply = await agent.run("What is 3 + 7?")
    print(reply)

asyncio.run(main())
```

For streamed replies, iterate over `run_stream()`:

```python
async for delta in agent.run_stream("Draft a short project update"):
  print(delta, end="", flush=True)
```

Want a different model? Pass a `provider` (or a `pydantic-ai` model directly):

```python
agent = create_minion("MyAgent", provider="anthropic")   # or "openai", "gemini"
agent = create_minion("MyAgent", provider="test")          # offline, no API key
```

### An agent with vector memory

```python
from miminions.memory.sqlite import SQLiteMemory
from miminions.agent import create_minion

with SQLiteMemory("agent.db") as memory:
  agent = create_minion("Assistant", memory=memory)

  # store_knowledge / recall_knowledge require an attached memory backend.
  agent.store_knowledge("Python is a high-level language", metadata={"topic": "python"})
  print(agent.recall_knowledge("What language is Python?"))
```

With memory attached, the agent also gains a built-in `ingest_document` tool that
chunks and stores `.pdf`/`.txt`/`.md` files. Requires the `[sqlite]` extra.

### Loading tools from an MCP server

```python
from mcp import StdioServerParameters
from miminions.agent import create_minion

agent = create_minion("MyAgent")
await agent.connect_mcp_server(
    "math", StdioServerParameters(command="python", args=["math_server.py"])
)
await agent.load_tools_from_mcp_server("math")
# ...
await agent.cleanup()
```

## CLI Usage

After install, the `miminions` command is available (a default workspace and
agent are created under `~/.miminions/` on first run):

```bash
miminions --help
python -m miminions --help        # equivalent
```

Command groups:

| Group | What it does |
| ----- | ------------ |
| `chat` | Interactive chat with a workspace agent; distills memory on exit |
| `prompt` | One-shot prompt to a workspace agent |
| `agent` | Create/manage agents and run/inspect their tools |
| `task` | Create and track tasks |
| `knowledge` | A versioned knowledge base |
| `workspace` | Manage workspaces, their nodes, rules, and on-disk files |
| `execution` | Register tools and record tool runs in execution sessions |
| `gateway` | Manage local gateway runtime, cron jobs, and gateway sessions |
| `auth` | Local sign-in, public-access mode, and config |

```bash
# Start an interactive chat (resume with --session <id>)
miminions chat start

# Show tool calls, token usage, and latency while chatting
miminions chat start --verbose

# One-shot prompt
miminions prompt ask "Summarize today's standup notes"

# Agents
miminions agent add --name "Researcher" --description "Finds and summarizes sources"
miminions agent list

# Workspaces
miminions workspace add --name "Demo" --sample --init-files
miminions workspace list
```

See the [CLI reference](https://miminions.ai/modules/cli/) for every subcommand.

## Documentation

| Topic | |
|-------|--|
| [Getting Started](https://miminions.ai/getting-started/) | Install, first agent, and the CLI |
| [Agent](https://miminions.ai/modules/agent/) | The `Minion` API |
| [Memory](https://miminions.ai/modules/memory/) | Three-tier and vector memory |
| [Context Builder](https://miminions.ai/modules/context/) | System-prompt assembly |
| [Tools](https://miminions.ai/modules/tools/) | `@tool`, `GenericTool`, MCP |
| [Workspaces](https://miminions.ai/modules/workspaces/) | Nodes, rules, on-disk layout |
| [Tasks & Workflows](https://miminions.ai/modules/tasks/) | `TaskRuntime` and tracing |
| [Data Management](https://miminions.ai/modules/data/) | `LocalDataManager` |
| [Gateway Runtime](https://miminions.ai/modules/gateway/) | Channels, bus, cron |

For a map of the source tree and module status, see [STRUCTURE.md](STRUCTURE.md).
Runnable examples live in [`examples/`](examples/).

## Development

```bash
git clone https://github.com/MiMinions-ai/MiMinions.git
cd MiMinions
pip install -e ".[dev]"
```

Run the tests:

```bash
pytest tests/                 # everything
pytest tests/unit/            # unit
pytest tests/integration/     # integration
pytest tests/e2e/             # end-to-end
```

### Publishing

`pyproject.toml` is the single source of truth for packaging. Build and publish
with `uv`:

```bash
uv build
uv publish
# TestPyPI:
uv publish --publish-url https://test.pypi.org/legacy/
```

Build a standalone CLI binary:

```bash
bash deploy/build_cli.sh
```

## Contributing

Contributions are welcome — see [CONTRIBUTING.md](CONTRIBUTING.md) and the
[Code of Conduct](CODE_OF_CONDUCT.md). Feature work targets the `development`
branch.

## License

MIT — see [LICENSE](LICENSE).
