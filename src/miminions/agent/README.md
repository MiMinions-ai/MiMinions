# MiMinions Agent

Pydantic-based agent with strong typing, validation, and structured schemas.

## Features
- **Structured Results**: Returns `ToolExecutionResult` models with status, result, error, and timing
- **Type Safety**: Full Pydantic validation for inputs, outputs, and tool schemas
- **Tool Registration**: Convert Python functions to tools with auto-generated JSON schemas
- **MCP Integration**: Load tools from Model Context Protocol servers
- **Memory Systems**: FAISS (in-memory vectors) or SQLite (persistent with keyword search)
- **LLM Ready**: JSON-serializable schemas for OpenAI, Anthropic, etc.

## Quick Start

```python
from miminions.agent import create_pydantic_agent, ExecutionStatus

agent = create_pydantic_agent("MyAgent")

def add(a: int, b: int) -> int:
    return a + b

agent.register_tool("add", "Add two numbers", add)

result = agent.execute("add", a=5, b=3)
print(result.status)  # ExecutionStatus.SUCCESS
print(result.result)  # 8
print(result.execution_time_ms)  # 0.15
```

## Documentation
- **QUICKSTART.md** - Usage guide
- **examples/** - Working examples
- **tests/** - Test suites
