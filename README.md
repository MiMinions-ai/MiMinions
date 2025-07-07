# MiMinions

A Python package for MiMinions - an agentic framework for multi-agent systems with knowledge retrieval, concept relations, and web search capabilities.

## Features

- **BaseAgent**: Core agent class with tool management
- **Vector Search**: Knowledge retrieval using pgvector for similarity search
- **GraphQL Queries**: Concept relation queries using pg_graphql
- **Web Search**: Exploratory search using Google and DuckDuckGo
- **Custom Tools**: Easy integration of custom tools and functions
- **Async Support**: Full asynchronous operation support
- **Graceful Dependencies**: Optional dependencies with graceful fallback

## Installation

You can install MiMinions using pip:

```bash
pip install miminions
```

For full functionality, install optional dependencies:

```bash
pip install miminions[full]
```

Or install individual components:

```bash
# For database operations (pgvector, pg_graphql)
pip install psycopg[binary] pgvector

# For web search
pip install googlesearch-python duckduckgo-search

# For async support
pip install aiohttp
```

## Quick Start

### Basic Agent with Custom Tools

```python
from miminions.agents import BaseAgent

# Create an agent
agent = BaseAgent(name="MyAgent")

# Add a custom tool
def calculator(operation, a, b):
    if operation == "add":
        return a + b
    elif operation == "multiply":
        return a * b
    else:
        return "Unknown operation"

agent.add_tool("calculator", calculator)

# Use the tool
result = agent.execute_tool("calculator", "add", 5, 3)
print(f"Result: {result}")  # Result: 8

agent.close()
```

### Agent with Database Operations

```python
from miminions.agents import BaseAgent

# Create agent with database connection
agent = BaseAgent(
    name="DatabaseAgent",
    connection_string="postgresql://user:password@localhost/database"
)

# Vector search for knowledge retrieval
results = agent.vector_search(
    query_vector=[0.1, 0.2, 0.3],
    table="knowledge_base",
    limit=5
)

# GraphQL query for concept relations
concept_data = agent.concept_query("""
    {
        concepts {
            id
            name
            relations {
                target
                type
            }
        }
    }
""")

agent.close()
```

### Web Search Operations

```python
from miminions.agents import BaseAgent

agent = BaseAgent(name="SearchAgent")

# Web search
results = agent.web_search("Python machine learning tutorial", num_results=5)

# Parallel search across multiple engines
parallel_results = await agent.parallel_search("AI research papers")

agent.close()
```

### Asynchronous Operations

```python
import asyncio
from miminions.agents import BaseAgent

async def main():
    agent = BaseAgent(name="AsyncAgent")
    
    # Add async tool
    async def async_processor(data):
        await asyncio.sleep(0.1)  # Simulate async work
        return f"Processed: {data}"
    
    agent.add_tool("processor", async_processor)
    
    # Use async tool
    result = await agent.execute_tool_async("processor", "test data")
    print(result)
    
    # Async knowledge search
    knowledge_results = await agent.knowledge_search_async(
        query="artificial intelligence",
        query_vector=[0.1, 0.2, 0.3],
        include_web_search=True
    )
    
    await agent.close_async()

asyncio.run(main())
```

## API Reference

### BaseAgent Class

#### Constructor
```python
BaseAgent(connection_string=None, max_workers=4, name="BaseAgent")
```

#### Tool Management
- `add_tool(name, tool_func)`: Add custom tool
- `remove_tool(name)`: Remove tool
- `list_tools()`: List available tools
- `has_tool(name)`: Check if tool exists
- `execute_tool(name, *args, **kwargs)`: Execute tool (sync)
- `execute_tool_async(name, *args, **kwargs)`: Execute tool (async)

#### Database Operations
- `vector_search(query_vector, table, ...)`: Vector similarity search
- `concept_query(query, variables=None)`: GraphQL query
- `vector_search_async(...)`: Async vector search
- `concept_query_async(...)`: Async GraphQL query

#### Web Search
- `web_search(query, num_results=10, prefer_engine=None)`: Web search
- `web_search_async(...)`: Async web search
- `parallel_search(query, num_results=10)`: Parallel multi-engine search

#### Knowledge Search
- `knowledge_search(query, ...)`: Combined knowledge and web search
- `knowledge_search_async(...)`: Async combined search

## Examples

See the `examples/` directory for more detailed usage examples.

## Development

To set up the development environment:

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
   ```
3. Run tests:
   ```bash
   pytest tests/
   ```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

