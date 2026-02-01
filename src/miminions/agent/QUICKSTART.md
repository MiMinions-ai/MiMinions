# Pydantic Agent Quick Start

Strongly-typed agent with Pydantic validation and structured results.

## Create an Agent

```python
import asyncio
from miminions.agent import create_pydantic_agent, ExecutionStatus

async def main():
    agent = create_pydantic_agent("MyAgent", "Optional description")
    
    # Register tools (auto-generates JSON schema from type hints)
    def add(a: int, b: int) -> int:
        return a + b
    
    agent.register_tool("add", "Add two numbers", add)
    
    # Execute - returns ToolExecutionResult model
    result = agent.execute("add", a=5, b=3)
    print(f"Status: {result.status}")  # ExecutionStatus.SUCCESS
    print(f"Result: {result.result}")  # 8
    print(f"Time: {result.execution_time_ms}ms")
    print(f"Error: {result.error}")  # None on success
    
    # Tool schemas (JSON-serializable for LLMs)
    schemas = agent.get_tools_schema()
    print(schemas)  # [{'name': 'add', 'parameters': {...}}]
    
    await agent.cleanup()

asyncio.run(main())
```

## Execution Styles

**Structured results with `execute()`:**
- Returns `ToolExecutionResult` with status, result, error, execution_time_ms
- No exceptions - errors returned in result object

```python
result = agent.execute("add", a=5, b=3)

if result.status == ExecutionStatus.SUCCESS:
    print(f"Success: {result.result}")
else:
    print(f"Failed: {result.error}")
```

**Raw results with `execute_tool()`:**
- Returns raw value directly
- Raises exceptions on error

```python
raw_result = agent.execute_tool("add", a=5, b=3)  # Returns 8 or raises
```

## With Memory

```python
from miminions.memory.faiss import FAISSMemory

memory = FAISSMemory(dim=384)
agent = create_pydantic_agent("MemoryAgent", memory=memory)

# Store knowledge
entry_id = agent.store_knowledge("Python is a programming language")

# Recall - returns MemoryQueryResult model
results = agent.get_memory_context("programming", top_k=5)
print(f"Query: {results.query}")
print(f"Count: {results.count}")
for entry in results.results:  # List[MemoryEntry]
    print(f"- {entry.text} (id: {entry.id})")
```

## Tool Schemas for LLM Integration

```python
# Get JSON schemas for all tools (ready for OpenAI, Anthropic, etc.)
schemas = agent.get_tools_schema()
# [
#   {
#     "name": "add",
#     "description": "Add two numbers",
#     "parameters": {
#       "type": "object",
#       "properties": {
#         "a": {"type": "integer"},
#         "b": {"type": "integer"}
#       },
#       "required": ["a", "b"]
#     }
#   }
# ]

# Execute from LLM tool call
from miminions.agent import ToolExecutionRequest

request = ToolExecutionRequest(
    tool_name="add",
    arguments={"a": 5, "b": 3}
)
result = agent.execute_request(request)
```

See `examples/pydantic_agent/` for complete examples and `tests/pydantic_agent/` for usage patterns.
