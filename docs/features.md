# Features & Use Cases

<!-- markdownlint-disable MD046 -->

Discover how autonomous AI agents are transforming industries and workflows.

MiMinions empowers developers to create intelligent, autonomous agents that
handle complex tasks, maintain context, and integrate seamlessly with external
tools. Explore real-world applications below.

---

## Knowledge-Aware AI Agents

`Memory & Context`{ .feature-badge }

Build agents with long-term memory using vector storage. Your agents can store,
recall, and update knowledge dynamically, maintaining context across
conversations.

- :material-check: Store and retrieve knowledge efficiently
- :material-check: Semantic search with similarity scoring
- :material-check: Update and manage memory entries
- :material-check: Context-aware responses

Attach a memory backend when you create the agent — `store_knowledge()` writes
straight into it.

```python
from miminions.memory.sqlite import SQLiteMemory
from miminions.agent import create_minion

with SQLiteMemory("agent.db") as memory:
    agent = create_minion("Assistant", memory=memory)

    agent.store_knowledge(
        "Python is a high-level programming language",
        metadata={"category": "programming"},
    )

    results = agent.recall_knowledge("What language is Python?")
```

!!! tip "Perfect for"

    - Customer support agents that remember user history
    - Personal assistants with long-term context
    - Research agents that accumulate knowledge
    - Educational tutors with personalised learning

!!! note "Memory is required"

    `store_knowledge()` and `recall_knowledge()` raise `ValueError` if no memory
    is attached. The `[sqlite]` extra (`pip install miminions[sqlite]`) installs
    the vector backend. See [Memory](modules/memory.md) for the full CRUD and
    search API.

---

## Streaming and Observable Agent Runs

`Agent Runtime`{ .feature-badge }

Stream responses as they are generated, bound provider requests with timeouts,
retry transient provider failures, and attach lightweight observability hooks for
tool calls, token usage, and latency.

- :material-check: Incremental `run_stream()` text deltas
- :material-check: Request timeouts and retry backoff for `run()`
- :material-check: Tool-call and turn-completion callbacks
- :material-check: Verbose CLI chat with tool, usage, and latency output

```python
from miminions.agent import create_minion


def show_tool(name, args):
    print(f"[tool] {name} {args}")


def show_usage(usage, latency):
    print(f"[turn] {usage.input_tokens} in / {usage.output_tokens} out, {latency:.1f}s")


agent = create_minion(
    "Reporter",
    request_timeout=30.0,
    max_retries=3,
    on_tool_call=show_tool,
    on_turn_end=show_usage,
)

async for delta in agent.run_stream("Draft a release summary"):
    print(delta, end="", flush=True)
```

!!! note "Retries and streaming"

    `run()` retries transient provider errors such as rate limits, 5xx responses,
    connection failures, and timeouts. `run_stream()` does not retry after output
    has begun, because already-yielded text cannot be withdrawn. See
    [Agent](modules/agent.md#timeouts-retries-hooks) for details.

---

## Intelligent Document Processing

`Document Intelligence`{ .feature-badge }

Ingest and process documents (PDFs, text, and Markdown) with automatic chunking
for optimal retrieval. Agents can understand and query document content with
semantic search.

- :material-check: PDF, text, and Markdown ingestion
- :material-check: Automatic text chunking with overlap
- :material-check: Semantic document search
- :material-check: Metadata tagging and filtering

With memory attached, the built-in `ingest_document` tool chunks the file and
stores every chunk in vector memory.

```python
from miminions.memory.sqlite import SQLiteMemory
from miminions.agent import create_minion

with SQLiteMemory("docs.db") as memory:
    agent = create_minion("DocAgent", memory=memory)

    result = agent.execute_tool("ingest_document", filepath="resume.pdf")
    print(result["chunks_stored"])

    # Now query the document semantically
    matches = agent.recall_knowledge("years of Python experience")
```

!!! tip "Perfect for"

    - Legal document analysis and Q&A
    - Resume screening and candidate matching
    - Research paper summarisation
    - Contract review and compliance

!!! warning "Requirements"

    `ingest_document` needs a memory backend attached. Supported file types are
    `.pdf`, `.txt`, `.md`, and `.text` — other extensions raise `ValueError`. PDF
    extraction requires the optional `pdfplumber` package
    (`pip install pdfplumber`).

---

## Model Context Protocol (MCP) Integration

`Tool Integration`{ .feature-badge }

Connect your agents to external tools and services using the Model Context
Protocol. Dynamically load and execute tools from MCP servers alongside custom
Python functions.

- :material-check: Connect to MCP servers
- :material-check: Load tools dynamically
- :material-check: Mix MCP and local functions
- :material-check: Async tool execution

Connect to a server, then load its tools into the agent's registry.

```python
from mcp import StdioServerParameters
from miminions.agent import create_minion

agent = create_minion("MathAgent")

await agent.connect_mcp_server(
    "math",
    StdioServerParameters(command="python", args=["math_server.py"]),
)
await agent.load_tools_from_mcp_server("math")

# MCP tools are now registered alongside any local functions
print(agent.list_tools())

await agent.cleanup()
```

!!! tip "Perfect for"

    - Workflow automation with external APIs
    - Data processing pipelines
    - Multi-tool agent orchestration
    - Integration with existing systems

!!! note "MCP package"

    MCP support requires the optional `mcp` package. See
    [Agent](modules/agent.md) for the full connect/load lifecycle.

---

## Persistent Knowledge with SQLite Memory

`Data Persistence`{ .feature-badge }

Use SQLite-backed memory for permanent knowledge storage that persists across
sessions. Perfect for agents that need to maintain state over time.

- :material-check: Persistent storage across sessions
- :material-check: CRUD operations on memory
- :material-check: Metadata, keyword, regex, and hybrid search
- :material-check: Custom database locations

Point `SQLiteMemory` at a file path and the knowledge survives process restarts.

```python
from miminions.memory.sqlite import SQLiteMemory
from miminions.agent import create_minion

with SQLiteMemory("agent_memory.db") as memory:
    agent = create_minion("PersistentAgent", memory=memory)

    agent.store_knowledge("User prefers concise answers", metadata={"type": "pref"})

    # Direct backend access for advanced search
    hits = memory.hybrid_search("concise", top_k=3)
    for hit in hits:
        print(hit["text"], hit["meta"])
```

!!! tip "Perfect for"

    - Multi-session conversations
    - Knowledge base management
    - User preference tracking
    - Audit trails and logging

!!! note "Result shape"

    `SQLiteMemory` search results are dicts with the keys `id`, `text`, `meta`,
    and (for vector reads) `distance`. The metadata key is `meta`, not
    `metadata`. Full API in [Memory](modules/memory.md).

---

## Ready to build your own agent?

Start creating autonomous AI agents with memory, tool integration, and document
processing capabilities.

[Get Started](getting-started.md){ .md-button .md-button--primary }
[Full Documentation](modules/agent.md){ .md-button }
[:fontawesome-brands-github: View on GitHub](https://github.com/MiMinions-ai/MiMinions){ .md-button }
