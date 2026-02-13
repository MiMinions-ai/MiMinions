# MiMinions Examples

Working examples for the Minion Agent.

## Examples

- `minion_agent_example.py` - Basic usage with structured results
- `pydantic_memory_example.py` - FAISS memory integration
- `sqlite_memory_example.py` - SQLite CRUD operations
- `sqlite_memory_search_example.py` - Vector and keyword search
- `document_ingestion_example.py` - PDF/text file processing

## Servers
- `servers/math_server.py` - Basic arithmetic MCP server
- `servers/document_server.py` - Document processing MCP server

## Running Examples

```bash
python examples/minion_agent_example.py
python examples/pydantic_memory_example.py
python examples/sqlite_memory_example.py
```

## What Each Example Demonstrates

### Basic Usage
- Tool registration from Python functions
- Structured result handling with ToolExecutionResult
- Tool discovery and inspection

### Memory Integration
- FAISS for in-memory vector search
- SQLite for persistent storage
- CRUD operations and search queries
- Metadata filtering

### Document Processing
- PDF and text file ingestion
- Automatic text chunking
- Vector storage for retrieval

### MCP Servers
- Connecting to MCP servers
- Dynamic tool loading
- Using remote tools
