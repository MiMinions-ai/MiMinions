# MiMinions Base Agent Module

## Overview

The base agent module provides a comprehensive foundation for creating AI agents with integrated capabilities for:

- **Knowledge Management**: Remember and recall functionality with vector-based storage
- **Session Tracking**: Conversation memory and context management
- **Knowledge Retrieval**: Vector-based search using pgvector
- **Concept Relations**: Graph-based queries using pg_graphql  
- **Web Search**: Exploratory search via Google and DuckDuckGo
- **Tool Management**: Custom tool integration system

## Architecture

### Core Components

1. **BaseAgent** (`src/miminions/agents/base_agent.py`)
   - Main agent class with tool management and session tracking
   - Remember/recall functionality for knowledge management
   - Synchronous and asynchronous operation support
   - Resource management and cleanup
   - Error handling and validation

2. **DatabaseTools** (`src/miminions/agents/tools/database.py`)
   - PostgreSQL connection management
   - Vector similarity search (pgvector)
   - Session-based conversation storage and retrieval
   - GraphQL query execution (pg_graphql)
   - Connection pooling and async support

3. **SearchTools** (`src/miminions/agents/tools/search.py`)
   - Google search integration
   - DuckDuckGo search integration
   - Parallel search capabilities
   - Automatic engine selection

### Key Features

#### Knowledge Management System
- **Remember**: Store information with vector embeddings
- **Recall**: Retrieve conversation history and context
- **Session Tracking**: Maintain conversation state across interactions
- **Context Search**: Vector-based relevance matching within sessions

#### Graceful Dependency Handling
- Optional dependencies don't break basic functionality
- Clear error messages when dependencies are missing
- Fallback behavior for unavailable components

#### Synchronous and Asynchronous APIs
- All major operations available in both sync and async versions
- Proper resource management with context managers
- Concurrent operation support

#### Internal Helper Functions
- All internal methods prefixed with underscore (`_`)
- Separation of public API and implementation details
- Consistent error handling patterns

## Usage Patterns

### Basic Agent Creation
```python
from miminions.agent.simple_agent import Agent

# Minimal agent (no database connection)
agent = Agent(name="MyAgent")

# Agent with database capabilities
agent = Agent(
    name="DatabaseAgent",
    connection_string="postgresql://user:pass@host/db"
)
```

### Tool Management
```python
# Add custom tools
def calculator(op, a, b):
    return a + b if op == "add" else a * b

agent.add_tool("calc", calculator)

# Execute tools
result = agent.execute_tool("calc", "add", 5, 3)

# Async tool execution
result = await agent.execute_tool_async("calc", "add", 5, 3)
```

### Knowledge Operations

#### Remember and Recall (New Memory System)
```python
# Create agent with session tracking
agent = BaseAgent(
    name="MemoryAgent",
    connection_string="postgresql://user:pass@host/db",
    session_id="conversation_123"
)

# Remember information
memory_id = agent.remember(
    content="User prefers Python for data science",
    embedding=[0.1, 0.2, 0.3],  # Optional vector embedding
    role="system",
    metadata={"topic": "preferences"}
)

# Search remembered knowledge
knowledge = agent.remember_search(
    query_vector=[0.1, 0.2, 0.3],
    limit=10
)

# Recall conversation history
history = agent.recall(limit=20)

# Recall relevant context using similarity
context = agent.recall_context(
    query_vector=[0.1, 0.2, 0.3],
    limit=5
)

# Session management
agent.set_session("new_conversation")
other_history = agent.recall(session_id="previous_conversation")
```

#### Legacy Vector Search (Deprecated)
```python
# Vector search (deprecated - use remember_search instead)
results = agent.vector_search(
    query_vector=[0.1, 0.2, 0.3],
    table="knowledge_base",
    limit=10
)

# GraphQL queries for concept relations
data = agent.concept_query("""
    { concepts { id name relations { type target } } }
""")

# Combined knowledge search
knowledge = agent.knowledge_search(
    query="machine learning",
    query_vector=[0.1, 0.2, 0.3],
    include_web_search=True
)
```

### Web Search
```python
# Basic web search
results = agent.web_search("AI research papers")

# Parallel search
parallel_results = await agent.parallel_search("deep learning")

# Engine-specific search
google_results = agent.search_tools.google_search("python tutorial")
ddg_results = agent.search_tools.duckduckgo_search("javascript guide")
```

## Error Handling

The module provides comprehensive error handling:

1. **Missing Dependencies**: Clear messages about required packages
2. **Database Connectivity**: Validation of connection strings and database state
3. **Search Engine Failures**: Graceful handling of search API errors
4. **Tool Errors**: Proper exception propagation from custom tools

## Testing

Run tests with:
```bash
pytest tests/test_base_agent.py -v
```

Tests cover:
- Basic agent initialization and session management
- Tool management operations
- Remember and recall functionality
- Error handling scenarios for missing database/search tools
- Resource cleanup and context management
- Dependency validation

## Future Enhancements

Potential areas for expansion:

1. **Multi-Agent Coordination**: Agent-to-agent communication
2. **Persistent State**: Agent state serialization/deserialization  
3. **Plugin System**: Dynamic tool loading
4. **Performance Monitoring**: Built-in metrics and logging
5. **Advanced Memory**: Semantic clustering and memory consolidation
6. **Cross-Session Analytics**: Pattern recognition across conversations

## Dependencies

### Required
- Python 3.8+
- typing-extensions

### Optional
- psycopg[binary] >= 3.1.0 (database operations)
- pgvector >= 0.2.0 (vector search)
- aiohttp >= 3.8.0 (async HTTP operations)
- googlesearch-python >= 1.2.0 (Google search)
- duckduckgo-search >= 3.9.0 (DuckDuckGo search)
- numpy >= 1.21.0 (vector operations)

## License

This module is part of the MiMinions project and is licensed under the MIT License.