# MiMinions Examples

Working examples for the Minion agent and supporting modules.

## Examples

- `minion_agent_example.py` - Basic tool registration and structured results
- `sqlite_memory_example.py` - SQLite memory CRUD and search operations
- `document_ingestion_example.py` - PDF/text document ingestion
- `tasks_example.py` - Task runtime examples with mock agents
- `example_chat/chat_example.py` - Chat example using a seeded workspace

## Running Examples

```bash
python examples/minion_agent_example.py
python examples/sqlite_memory_example.py
python examples/document_ingestion_example.py
python examples/tasks_example.py
```

## What Each Example Demonstrates

### Basic Usage
- Tool registration from Python functions
- Structured result handling with ToolExecutionResult
- Tool discovery and inspection

### Memory Integration
- SQLite for persistent storage
- CRUD operations and search queries
- Metadata filtering

### Document Processing
- PDF and text file ingestion
- Automatic text chunking
- Vector storage for retrieval

