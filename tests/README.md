# MiMinions Tests

Comprehensive test suites for the Pydantic Agent.

## Test Files

- `test_pydantic_agent.py` - Core agent functionality with Pydantic models
- `test_pydantic_memory.py` - Memory with structured results
- `test_sqlite_memory.py` - SQLite CRUD operations
- `test_sqlite_memory_search.py` - Vector and keyword search
- `test_document_ingestion.py` - Document processing

- **cli/** - CLI interface tests
- **data/** - Data management system tests

## Running Tests

```bash
python tests/test_pydantic_agent.py
python tests/test_pydantic_memory.py
python tests/test_sqlite_memory.py
python tests/test_sqlite_memory_search.py
python tests/test_document_ingestion.py
```

## Test Coverage

### Agent Core
- Tool registration and execution
- Structured result validation (ToolExecutionResult)
- Error handling with status codes
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
