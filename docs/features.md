# Features & Use Cases

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

```python
agent.store_knowledge(
    "Python is a high-level programming language",
    metadata={"category": "programming"},
)
```

!!! tip "Perfect for"

    - Customer support agents that remember user history
    - Personal assistants with long-term context
    - Research agents that accumulate knowledge
    - Educational tutors with personalised learning

---

## Intelligent Document Processing

`Document Intelligence`{ .feature-badge }

Ingest and process documents (PDFs, text files) with automatic chunking for
optimal retrieval. Agents can understand and query document content with
semantic search.

- :material-check: PDF and text file ingestion
- :material-check: Automatic text chunking with overlap
- :material-check: Semantic document search
- :material-check: Metadata tagging and filtering

```python
result = agent.execute_tool(
    "ingest_document",
    filepath="resume.pdf",
)
```

!!! tip "Perfect for"

    - Legal document analysis and Q&A
    - Resume screening and candidate matching
    - Research paper summarisation
    - Contract review and compliance

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

```python
await agent.connect_mcp_server("math_server", server_params)
await agent.load_tools_from_mcp_server("math_server")
```

!!! tip "Perfect for"

    - Workflow automation with external APIs
    - Data processing pipelines
    - Multi-tool agent orchestration
    - Integration with existing systems

---

## Persistent Knowledge with SQLite Memory

`Data Persistence`{ .feature-badge }

Use SQLite-backed memory for permanent knowledge storage that persists across
sessions. Perfect for agents that need to maintain state over time.

- :material-check: Persistent storage across sessions
- :material-check: CRUD operations on memory
- :material-check: Custom database locations
- :material-check: Metadata filtering and search

```python
memory = SQLiteMemory(db_path="agent_memory.db")
agent = create_simple_agent("PersistentAgent", memory=memory)
```

!!! tip "Perfect for"

    - Multi-session conversations
    - Knowledge base management
    - User preference tracking
    - Audit trails and logging

---

## Ready to build your own agent?

Start creating autonomous AI agents with memory, tool integration, and document
processing capabilities.

[Get Started](getting-started.md){ .md-button .md-button--primary }
[Full Documentation](modules/agent.md){ .md-button }
[:fontawesome-brands-github: View on GitHub](https://github.com/MiMinions-ai/MiMinions){ .md-button }
