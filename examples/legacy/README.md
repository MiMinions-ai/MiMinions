# MiMinions Examples

This directory contains comprehensive examples demonstrating the capabilities of the MiMinions BaseAgent.

## Available Examples

### 1. `simple_agent_example.py`
Simple agent creation and tool usage:
- Initialize an agent with a custom name and session
- Register and execute basic tools

### 2. `custom_tools_example.py`
Advanced custom tool creation and management:
- Basic tool registration and execution
- Advanced tools with multiple operations
- Async tool operations
- Error handling in tools
- Tool composition and dynamic creation

## Running the Examples

### Prerequisites

1. Install the package in development mode:
   ```bash
   pip install -e .
   ```

2. For database examples, you'll need:
   - PostgreSQL with pgvector extension
   - pg_graphql extension
   - Valid connection string

3. For search examples, you'll need:
   - Google Search API credentials
   - DuckDuckGo search (optional)

### Running Individual Examples

```bash
# Basic agent functionality
python examples/base_agent_example.py

# Memory management features
python examples/memory_management_example.py

# Custom tools and composition
python examples/custom_tools_example.py

# Database integration (requires actual database)
python examples/database_integration_example.py
```

## Example Categories

### Basic Usage
- Agent initialization with custom names and sessions
- Tool registration, execution, and removal
- Session management and switching
- Error handling without dependencies

### Memory Management
- `remember()` - Store information with vector embeddings
- `recall()` - Retrieve conversation history by session
- `remember_search()` - Vector similarity search in knowledge
- `recall_context()` - Find relevant context using embeddings

### Database Operations
- Vector search with pgvector
- GraphQL queries with pg_graphql
- Session-based conversation storage
- Cross-session knowledge retrieval

### Custom Tools
- Simple function registration
- Complex multi-operation tools
- Async tool operations
- Tool composition and chaining
- Dynamic tool creation

### Advanced Features
- Async/await support for all operations
- Context managers for resource cleanup
- Graceful error handling for missing dependencies
- Parallel operations and search

## Notes

- Examples work without actual database/search dependencies by showing expected behavior
- Error handling demonstrates what happens when optional dependencies are missing
- All examples include both sync and async variants where applicable
- Examples are self-contained and can be run independently

## Testing

The examples are designed to run without external dependencies by gracefully handling missing services and showing what would happen with proper setup.

For actual functionality, ensure you have:
- Database connection for remember/recall features
- Search API keys for web search capabilities
- Proper network connectivity for external services