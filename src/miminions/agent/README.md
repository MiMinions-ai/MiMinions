# MiMinions Agents

Two agent implementations with identical functionality:

## Simple Agent
- Returns raw values from tool execution
- Raises exceptions on errors
- Best for: Quick prototyping, simple scripts, legacy code compatibility

## Pydantic Agent
- Returns structured `ToolExecutionResult` models with validation
- No exceptions - errors in result object
- Includes execution timing
- JSON-serializable tool schemas for LLM integration
- Best for: Production code, LLM integration, type-safe applications

## Features (Both Agents)
- **Tool Registration**: Convert Python functions to agent tools with auto-generated schemas
- **MCP Integration**: Load tools from Model Context Protocol servers
- **Memory Systems**: FAISS (in-memory vectors) or SQLite (persistent with keyword search)
- **Tool Discovery**: List, search, and inspect tools programmatically

## Quick Start

```python
from miminions.agent import create_simple_agent, create_pydantic_agent

# Simple Agent - direct results or exceptions
agent = create_simple_agent("MyAgent")
result = agent.execute_tool("add", a=5, b=3)  # Returns: 8

# Pydantic Agent - structured results
agent = create_pydantic_agent("MyAgent")
result = agent.execute("add", a=5, b=3)
print(result.status)  # ExecutionStatus.SUCCESS
print(result.result)  # 8
print(result.execution_time_ms)  # 0.15
```

## Documentation
- **simple_agent/QUICKSTART.md** - Simple Agent usage guide
- **pydantic_agent/QUICKSTART.md** - Pydantic Agent usage guide  
- **examples/** - Complete working examples for both agents
- **tests/** - Test suites showing usage patterns

## Choosing an Agent

| Scenario | Recommended |
|----------|-------------|
| Quick prototype | Simple Agent |
| Production application | Pydantic Agent |
| LLM integration | Pydantic Agent |
| Type safety required | Pydantic Agent |
| Legacy compatibility | Simple Agent |
| Need execution metrics | Pydantic Agent |
