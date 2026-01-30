# MiMinions Tests

Comprehensive test suites for all agent implementations.

## Directory Structure

- **simple_agent/** - Simple Agent tests
  - `test_simple_agent.py` - Core agent functionality
  - `test_memory.py` - FAISS memory integration
  - `test_sqlite_memory.py` - SQLite CRUD operations
  - `test_sqlite_memory_search.py` - Vector and keyword search
  - `test_document_ingestion.py` - Document processing

- **pydantic_agent/** - Pydantic Agent tests (mirrors simple_agent)
  - `test_pydantic_agent.py` - Core functionality with Pydantic models
  - `test_pydantic_memory.py` - Memory with structured results
  - `test_sqlite_memory.py` - SQLite with ToolExecutionResult
  - `test_sqlite_memory_search.py` - Search with result models
  - `test_document_ingestion.py` - Document processing with validation

- **cli/** - CLI interface tests
- **data/** - Data management system tests

## Running Tests

```bash
# Simple Agent tests
python tests/simple_agent/test_simple_agent.py
python tests/simple_agent/test_memory.py
python tests/simple_agent/test_sqlite_memory.py
python tests/simple_agent/test_sqlite_memory_search.py
python tests/simple_agent/test_document_ingestion.py

# Pydantic Agent tests (same test names)
python tests/pydantic_agent/test_pydantic_agent.py
python tests/pydantic_agent/test_pydantic_memory.py
python tests/pydantic_agent/test_sqlite_memory.py
python tests/pydantic_agent/test_sqlite_memory_search.py
python tests/pydantic_agent/test_document_ingestion.py
```

## Test Coverage

Both agent test suites cover identical functionality:

### Agent Core
- Tool registration and execution
- Error handling (exceptions vs result objects)
- Tool discovery and search
- MCP server integration
- Async operations

### Memory Systems
- FAISS: Create, read, update, delete operations
- SQLite: CRUD with persistence
- Vector similarity search
- Keyword search and filtering
- Metadata queries

### Document Processing
- PDF file ingestion
- Text file processing
- Automatic chunking
- Memory storage and retrieval

## Key Differences

**Simple Agent tests**: Check for exceptions and raw return values
**Pydantic Agent tests**: Validate result models and status codes
