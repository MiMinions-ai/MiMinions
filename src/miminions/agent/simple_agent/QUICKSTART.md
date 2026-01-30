# Simple Agent Quick Start

Lightweight agent that returns raw values and raises exceptions on errors.

## Create an Agent

```python
import asyncio
from miminions.agent.simple_agent import create_simple_agent

async def main():
    agent = create_simple_agent("MyAgent", "Optional description")
    
    # Register Python functions as tools
    def add(a: int, b: int) -> int:
        return a + b
    
    agent.add_function_as_tool("add", "Add two numbers", add)
    
    # Execute tools - returns raw result or raises exception
    result = agent.execute_tool("add", a=5, b=3)
    print(f"Result: {result}")  # 8
    
    # Tool discovery
    print(agent.list_tools())  # ['add']
    print(agent.get_tool_info("add"))
    
    await agent.cleanup()

asyncio.run(main())
```

## With Memory

```python
from miminions.memory.faiss import FAISSMemory
from miminions.memory.sqlite import SQLiteMemory

# FAISS (in-memory vector search)
memory = FAISSMemory(dim=384)
agent = create_simple_agent("MemoryAgent", memory=memory)

# Or SQLite (persistent storage with vector + keyword search)
memory = SQLiteMemory(db_path="memory.db")
agent = create_simple_agent("MemoryAgent", memory=memory)

# Store and recall knowledge
entry_id = agent.store_knowledge("Python is a programming language", metadata={"topic": "coding"})
results = agent.recall_knowledge("programming", top_k=5)
for r in results:
    print(f"{r['text']} (score: {r['distance']:.3f})")
```

## With MCP Server

```python
from mcp import StdioServerParameters

# Connect to MCP server (e.g., math operations, file tools)
server_params = StdioServerParameters(
    command="python3",
    args=["examples/servers/math_server.py"]
)

await agent.connect_mcp_server("math_server", server_params)
tools = await agent.load_tools_from_mcp_server("math_server")
print(f"Loaded {len(tools)} tools from MCP server")

# Use MCP tools like regular tools
result = agent.execute_tool("add", a=10, b=20)  # 30
```

## Error Handling

```python
try:
    result = agent.execute_tool("missing_tool", x=1)
except ValueError as e:
    print(f"Tool not found: {e}")

try:
    result = agent.execute_tool("add", wrong_param=5)
except RuntimeError as e:
    print(f"Execution failed: {e}")
```

See `examples/simple_agent/` for complete examples and `tests/simple_agent/` for usage patterns.
