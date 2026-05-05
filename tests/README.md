# MiMinions Tests

Comprehensive test suites for the Minion Agent.

## Test Files

- **general/** - Core agent functionality, memory, and general test cases
- **cli/** - CLI interface tests
- **data/** - Data management system tests
- **gateway/** - Gateway integration tests
- **task/** - Task management tests

## Running Tests

To run the complete test suite across all subfolders automatically, you can use the newly provided script:

```bash
./tests/run_all.sh
```

This bash script simplifies test execution by automatically navigating to the project root and running `pytest tests/` with the appropriate verbosity flags.

## Test Coverage

### Agent Core
- Tool registration and execution
- Structured result validation (ToolExecutionResult)
- Error handling with status codes
- Tool discovery and search
- MCP server integration
- Async operations

### Memory Systems
- SQLite: CRUD with persistence
- Vector similarity search
- Keyword search and filtering
- Metadata queries

### Document Processing
- PDF file ingestion
- Text file processing
- Automatic chunking
- Memory storage and retrieval

## Important Note on Running Tests

Some test files in this repository may include an `if __name__ == "__main__":` block
for direct execution. However, this project is designed to use `pytest` as the primary
test runner.

Running test files directly (e.g., `python tests/test_file.py`) is not guaranteed to
work correctly in all cases.

Recommended approach:
```bash
./tests/run_all.sh
```

Or run specific test files:
```bash
python -m pytest tests/cli/test_chat.py
python -m pytest tests/test_context_builder.py
```

This ensures:
- proper fixture handling
- correct test discovery
- consistent environment setup