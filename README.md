# MiMinions

A Python package for MiMinions - an agentic framework for multi-agent systems with knowledge retrieval, concept relations, and web search capabilities.

## Features

- **Generic Tool System**: Create tools once, use with multiple AI frameworks
- **Framework Adapters**: Support for LangChain, AutoGen, and AGNO
- **Agent Support**: Simple agent class for managing tools
- **Type Safety**: Full type annotation support
- **BaseAgent**: Core agent class with tool management and session tracking
- **Remember & Recall**: Knowledge management with vector-based storage and conversation memory
- **Vector Search**: Knowledge retrieval using pgvector for similarity search  
- **GraphQL Queries**: Concept relation queries using pg_graphql
- **Web Search**: Exploratory search using Google and DuckDuckGo
- **Custom Tools**: Easy integration of custom tools and functions
- **Session Management**: Conversation tracking and context management
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
from miminions.agent import BaseAgent

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
from miminions.agent import BaseAgent

# Create agent with database connection
agent = BaseAgent(
    name="DatabaseAgent",
    connection_string="postgresql://user:password@localhost/database"
)

# Remember information (stores with vector embedding)
memory_id = agent.remember(
    content="Python is a programming language",
    embedding=[0.1, 0.2, 0.3],  # Optional: your embedding
    role="system"
)

# Search remembered knowledge
results = agent.remember_search(
    query_vector=[0.1, 0.2, 0.3],
    limit=5
)

# Recall conversation history
history = agent.recall(limit=10)

# Recall relevant context using vector similarity
context = agent.recall_context(
    query_vector=[0.1, 0.2, 0.3],
    limit=5
)

# Legacy vector search (deprecated - use remember_search instead)
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

### Session Management

```python
from miminions.agent import BaseAgent

# Create agent with specific session
agent = BaseAgent(
    name="SessionAgent",
    connection_string="postgresql://user:password@localhost/database",
    session_id="conversation_123"
)

# Remember user input
agent.remember("Hello, how are you?", role="user")

# Remember assistant response  
agent.remember("I'm doing well, thank you!", role="assistant")

# Recall entire conversation
conversation = agent.recall()

# Switch to different session
agent.set_session("conversation_456")

# Recall from specific session
history = agent.recall(session_id="conversation_123")

agent.close()
```

### Web Search Operations

```python
from miminions.agent import BaseAgent

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
from miminions.agent import BaseAgent

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

#### Agentic Tooling System

```python
from miminions.tools import tool
from miminions.agent import Agent

# Create a tool
@tool(name="calculator", description="Simple calculator")
def calculate(operation: str, a: int, b: int) -> int:
    if operation == "add":
        return a + b
    elif operation == "subtract":
        return a - b
    else:
        return 0

# Create an agent and add the tool
agent = Agent("my_agent", "A helpful agent")
agent.add_tool(calculate)

# Use the tool
result = agent.execute_tool("calculator", operation="add", a=5, b=3)
print(result)  # 8

# Convert to different frameworks
langchain_tools = agent.to_langchain_tools()
autogen_tools = agent.to_autogen_tools()
agno_tools = agent.to_agno_tools()
```

### Workspace Management

Manage workspaces with nodes, rules, and state-based logic:

```bash
# List all workspaces
miminions workspace list

# Add a new workspace
miminions workspace add --name "My Workspace" --description "Workspace description"

# Add a sample workspace with example nodes and rules
miminions workspace add --name "Demo Workspace" --description "Demo workspace" --sample

# Show workspace details
miminions workspace show workspace_id

# Update a workspace
miminions workspace update workspace_id --name "New Name" --description "New description"

# Remove a workspace
miminions workspace remove workspace_id

# Add a node to a workspace
miminions workspace add-node workspace_id --name "Node Name" --type agent --properties '{"key": "value"}'

# Connect two nodes in a workspace
miminions workspace connect-nodes workspace_id node1_id node2_id

# Set workspace state
miminions workspace set-state workspace_id --key "priority" --value "high"

# Evaluate workspace logic and see applicable actions
miminions workspace evaluate workspace_id
```

#### Workspace Features

- **Network of Nodes**: Create and connect nodes of different types (agent, task, workflow, knowledge, custom)
- **Rule System**: Define rules with conditions and actions that trigger based on workspace state
- **Rule Inheritance**: Inherit rules from parent workspaces to create hierarchical rule sets
- **State-based Logic**: Rules evaluate against current workspace state to determine applicable actions
- **Node Types**: Support for agent, task, workflow, knowledge, and custom node types
- **Connections**: Bidirectional connections between nodes to represent relationships

## Framework Compatibility

The generic tool system is inter-transferable with:

- **LangChain**: Convert to/from LangChain BaseTool
- **AutoGen**: Convert to/from AutoGen FunctionTool
- **AGNO**: Convert to/from AGNO Function

## Documentation

See `TOOLS_README.md` for detailed documentation of the tool system.

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

### Running Tests

The package includes comprehensive tests for the CLI:

```bash
# Run basic tests
python src/tests/cli/test_runner.py

# Run specific test files (if pytest is available)
pytest src/tests/cli/test_auth.py
pytest src/tests/cli/test_agent.py
pytest src/tests/cli/test_e2e.py
```

### CLI Architecture

The CLI is organized into modules:

- `src/interface/cli/main.py` - Main CLI entry point
- `src/interface/cli/auth.py` - Authentication commands
- `src/interface/cli/agent.py` - Agent management commands
- `src/interface/cli/task.py` - Task management commands
- `src/interface/cli/workflow.py` - Workflow management commands
- `src/interface/cli/knowledge.py` - Knowledge management commands
- `src/interface/cli/workspace.py` - Workspace management commands

Data is stored locally in JSON files in the `~/.miminions/` directory.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

