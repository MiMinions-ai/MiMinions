# Quick Start Guide: MiMinions Agents

## Overview

MiMinions provides two agent implementations:

1. **Simple Agent** - Lightweight agent with MCP server support and memory integration
2. **Pydantic Agent** - Strongly-typed agent using Pydantic models for validation

Both agents support:
- Tool registration and execution
- MCP (Model Context Protocol) server integration
- Memory integration for knowledge storage and retrieval

## Which Agent Should I Use?

| Use Case | Recommended Agent |
|----------|-------------------|
| Quick prototyping | Simple Agent |
| Production with type safety | Pydantic Agent |
| Legacy code compatibility | Simple Agent |
| Future LLM integration | Pydantic Agent |
| Strong validation needed | Pydantic Agent |

## Quick Start: Simple Agent

```python
import asyncio
from miminions.agent import create_simple_agent

async def main():
    agent = create_simple_agent("MyAgent")
    
    def add(a: int, b: int) -> int:
        return a + b
    
    agent.add_function_as_tool("add", "Add two numbers", add)
    result = agent.execute_tool("add", a=1, b=2)
    print(f"Result: {result}")  # Result: 3
    
    await agent.cleanup()

asyncio.run(main())
```

📚 **Full documentation:** [simple_agent/QUICKSTART.md](simple_agent/QUICKSTART.md)

## Quick Start: Pydantic Agent

```python
import asyncio
from miminions.agent import create_pydantic_agent

async def main():
    agent = create_pydantic_agent("MyAgent")
    
    def add(a: int, b: int) -> int:
        return a + b
    
    agent.register_tool("add", "Add two numbers", add)
    result = agent.execute("add", a=1, b=2)
    
    print(f"Status: {result.status}")   # Status: success
    print(f"Result: {result.result}")   # Result: 3
    
    await agent.cleanup()

asyncio.run(main())
```

📚 **Full documentation:** [pydantic_agent/QUICKSTART.md](pydantic_agent/QUICKSTART.md)

## Memory Integration

Both agents support the same memory interface:

```python
from miminions.memory.faiss import FAISSMemory

memory = FAISSMemory(dim=384)
agent = create_simple_agent("MemoryAgent", memory=memory)
# or
agent = create_pydantic_agent("MemoryAgent", memory=memory)

# Store knowledge
agent.store_knowledge("Python is great", metadata={"topic": "programming"})

# Recall knowledge
results = agent.recall_knowledge("programming")
```

## MCP Server Integration

Both agents support MCP servers:

```python
from mcp import StdioServerParameters

server_params = StdioServerParameters(
    command="python3",
    args=["your_server.py"]
)

await agent.connect_mcp_server("my_server", server_params)
await agent.load_tools_from_mcp_server("my_server")
```

## Next Steps

- **Simple Agent:** See [simple_agent/QUICKSTART.md](simple_agent/QUICKSTART.md)
- **Pydantic Agent:** See [pydantic_agent/QUICKSTART.md](pydantic_agent/QUICKSTART.md)
- **Examples:** Check the `examples/` directory
- **Tests:** Run the test suite in `tests/`
- Build more complex multi-agent systems