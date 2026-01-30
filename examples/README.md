# MiMinions Examples

Complete working examples for both agent implementations.

## Directory Structure

- **simple_agent/** - Simple Agent examples (raw results, exceptions)
  - `simple_agent_example.py` - Basic usage and MCP integration
  - `agent_memory_example.py` - FAISS memory integration
  - `sqlite_memory_example.py` - SQLite CRUD operations
  - `sqlite_memory_search_example.py` - Vector and keyword search
  - `document_ingestion_example.py` - PDF/text file processing
  - `document_server_example.py` - MCP document server usage

- **pydantic_agent/** - Pydantic Agent examples (structured results, validation)
  - `pydantic_agent_example.py` - Basic usage with structured results
  - `pydantic_memory_example.py` - Memory with Pydantic models
  - `sqlite_memory_example.py` - SQLite with structured responses
  - `sqlite_memory_search_example.py` - Search with result models
  - `document_ingestion_example.py` - Document processing with validation

- **servers/** - Sample MCP servers
  - `math_server.py` - Basic arithmetic operations
  - `document_server.py` - Document processing tools

## Running Examples

```bash
# Simple Agent examples
python examples/simple_agent/simple_agent_example.py
python examples/simple_agent/agent_memory_example.py
python examples/simple_agent/sqlite_memory_example.py

# Pydantic Agent examples
python examples/pydantic_agent/pydantic_agent_example.py
python examples/pydantic_agent/pydantic_memory_example.py

# Test MCP servers
python examples/servers/math_server.py  # Run as standalone server
```

## What Each Example Demonstrates

### Basic Usage
- Tool registration from Python functions
- Tool execution and error handling
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
