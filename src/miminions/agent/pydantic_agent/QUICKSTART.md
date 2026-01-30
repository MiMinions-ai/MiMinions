# Quick Start Guide: Pydantic Agent

## Overview

The Pydantic Agent is a strongly-typed agent implementation that uses Pydantic models for:
- Tool definitions and schemas
- Input validation
- Execution requests and results
- Memory entries and queries

It mirrors the Simple Agent's capabilities but provides:
- Strong typing and validation
- JSON-serializable schemas (ready for LLM integration)
- Structured execution results with timing
- Pydantic models for all data structures

## Installation

```bash
pip install pydantic>=2.0.0 mcp[cli]>=1.15.0
```

## Basic Usage

### 1. Create an Agent

```python
import asyncio
from miminions.agent.pydantic_agent import create_pydantic_agent

async def main():
    # Create agent
    agent = create_pydantic_agent("MyAgent", "Description of my agent")
    
    print(f"Agent state: {agent.get_state()}")
    
    await agent.cleanup()

asyncio.run(main())
```

### 2. Register Tools

```python
from miminions.agent.pydantic_agent import create_pydantic_agent

agent = create_pydantic_agent("ToolAgent")

def add(a: int, b: int) -> int:
    """Add two numbers"""
    return a + b

def greet(name: str, formal: bool = False) -> str:
    """Greet a user"""
    return f"{'Good day' if formal else 'Hello'}, {name}!"

# Register tools (schema is auto-extracted from function signature)
agent.register_tool("add", "Add two numbers", add)
agent.register_tool("greet", "Greet someone", greet)

print(f"Available tools: {agent.list_tools()}")
```

### 3. Execute Tools

There are two ways to execute tools:

#### Pydantic-style (recommended for new code)

```python
from miminions.agent.pydantic_agent import ToolExecutionRequest

# Execute and get structured result
result = agent.execute("add", a=5, b=3)

print(f"Status: {result.status}")        # ExecutionStatus.SUCCESS
print(f"Result: {result.result}")        # 8
print(f"Time: {result.execution_time_ms}ms")

# Or use a request object
request = ToolExecutionRequest(tool_name="greet", arguments={"name": "Alice"})
result = agent.execute_request(request)
print(f"Greeting: {result.result}")
```

#### Simple Agent compatible style

```python
# Direct execution (raises exceptions on error)
result = agent.execute_tool("add", a=5, b=3)
print(f"Result: {result}")  # 8
```

## Tool Schemas

The Pydantic Agent automatically generates JSON schemas from function signatures:

```python
# Get all tool schemas (JSON-serializable, ready for LLM)
schemas = agent.get_tools_schema()
print(schemas)
# [
#   {
#     "name": "add",
#     "description": "Add two numbers",
#     "parameters": {
#       "type": "object",
#       "properties": {
#         "a": {"type": "integer", "description": "a"},
#         "b": {"type": "integer", "description": "b"}
#       },
#       "required": ["a", "b"]
#     }
#   }
# ]

# Get single tool definition
tool_def = agent.get_tool("add")
print(tool_def.to_dict())
```

## Working with Memory

The Pydantic Agent supports the same memory interface as Simple Agent:

```python
from miminions.agent.pydantic_agent import create_pydantic_agent
from miminions.memory.faiss import FAISSMemory

async def memory_example():
    memory = FAISSMemory(dim=384)
    agent = create_pydantic_agent("MemoryAgent", memory=memory)
    
    # Store knowledge (returns entry ID)
    entry_id = agent.store_knowledge(
        "Python is a high-level programming language",
        metadata={"topic": "programming"}
    )
    
    # Recall knowledge (returns Pydantic model)
    results = agent.get_memory_context("programming languages", top_k=3)
    print(f"Query: {results.query}")
    print(f"Found {results.count} results")
    for entry in results.results:
        print(f"  - {entry.text}")
    
    await agent.cleanup()
```

## MCP Server Integration

```python
from mcp import StdioServerParameters
from miminions.agent.pydantic_agent import create_pydantic_agent

async def mcp_example():
    agent = create_pydantic_agent("MCPAgent")
    
    server_params = StdioServerParameters(
        command="python3",
        args=["your_mcp_server.py"]
    )
    
    await agent.connect_mcp_server("my_server", server_params)
    tool_definitions = await agent.load_tools_from_mcp_server("my_server")
    
    print(f"Loaded {len(tool_definitions)} tools")
    
    # Execute MCP tools asynchronously
    result = await agent.execute_async("mcp_tool_name", param=value)
    
    await agent.cleanup()
```

## Differences from Simple Agent

| Feature | Simple Agent | Pydantic Agent |
|---------|--------------|----------------|
| Type Safety | Runtime only | Pydantic validation |
| Execution Result | Raw value or exception | `ToolExecutionResult` model |
| Memory Context | Dict | `MemoryQueryResult` model |
| Tool Schema | Dict | `ToolDefinition` model |
| Agent State | Properties | `AgentState` model |
| Error Handling | Exceptions | Result object with error field |
| Execution Timing | Not tracked | Included in result |

## Error Handling

### Pydantic-style (no exceptions)

```python
result = agent.execute("nonexistent_tool")

if result.status == ExecutionStatus.ERROR:
    print(f"Error: {result.error}")
else:
    print(f"Result: {result.result}")
```

### Simple Agent compatible style (exceptions)

```python
try:
    result = agent.execute_tool("nonexistent_tool")
except ValueError as e:
    print(f"Tool not found: {e}")
except RuntimeError as e:
    print(f"Execution error: {e}")
```

## Custom Tool Schemas

For complex tools, you can define explicit schemas:

```python
from miminions.agent.pydantic_agent import (
    ToolSchema, ToolParameter, ParameterType
)

# Define explicit schema
schema = ToolSchema(parameters=[
    ToolParameter(
        name="data",
        type=ParameterType.OBJECT,
        description="The data to process",
        required=True
    ),
    ToolParameter(
        name="options",
        type=ParameterType.OBJECT,
        description="Processing options",
        required=False,
        default={}
    )
])

def process_data(data: dict, options: dict = None) -> dict:
    """Process data with options"""
    return {"processed": data, "options": options or {}}

agent.register_tool("process", "Process data", process_data, schema=schema)
```

## Best Practices

1. **Use the Pydantic-style execution** (`execute()`) for new code - it provides structured results and doesn't raise exceptions
2. **Check `result.status`** instead of catching exceptions
3. **Use `get_tools_schema()`** when preparing tool definitions for LLM integration
4. **Leverage type hints** in your functions for automatic schema generation
5. **Use `AgentState`** to inspect agent configuration

## Testing

Run the test suite:
```bash
python3 tests/pydantic_agent/test_pydantic_agent.py
```

Run examples:
```bash
python3 examples/pydantic_agent/pydantic_agent_example.py
```

## Future LLM Integration

The Pydantic Agent is designed to be extended with an LLM. The key integration points are:

1. **`get_tools_schema()`** - Returns JSON-serializable tool definitions
2. **`execute_request()`** - Accepts structured `ToolExecutionRequest` objects
3. **`ToolExecutionResult`** - Provides structured results for LLM consumption

When adding an LLM, you would:
1. Convert `get_tools_schema()` output to your LLM's tool format
2. Parse LLM tool calls into `ToolExecutionRequest` objects
3. Execute with `execute_request()` and feed results back to the LLM

```python
# Future pattern (LLM not yet implemented)
schemas = agent.get_tools_schema()
llm_response = llm.generate(prompt, tools=schemas)

if llm_response.has_tool_call:
    request = ToolExecutionRequest(
        tool_name=llm_response.tool_name,
        arguments=llm_response.tool_arguments
    )
    result = agent.execute_request(request)
    # Feed result back to LLM...
```
