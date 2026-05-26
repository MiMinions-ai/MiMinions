# Getting Started

## Installation

Install from PyPI:

```bash
pip install miminions
```

Or with `uv`:

```bash
uv add miminions
```

For SQLite vector memory support:

```bash
pip install miminions[sqlite]
```

## Requirements

- Python 3.10+
- An [OpenRouter](https://openrouter.ai/) API key (set as `OPENROUTER_API_KEY`)

## Your First Agent

```python
import asyncio
from miminions.agent import create_minion

async def main():
    agent = create_minion("MyAgent")

    def calculator(operation: str, a: int, b: int) -> int:
        if operation == "add":
            return a + b
        elif operation == "multiply":
            return a * b
        return 0

    agent.register_tool("calculator", "Perform arithmetic", calculator)
    reply = await agent.run("What is 6 multiplied by 7?")
    print(reply)

asyncio.run(main())
```

## Using the CLI

After install, the `miminions` CLI is available:

```bash
miminions --help
```

Start an interactive chat session:

```bash
miminions chat start
```

Resume a previous session by ID:

```bash
miminions chat start --session <session_id>
```

## Workspace Management

```bash
# List all workspaces
miminions workspace list

# Create a workspace with sample data
miminions workspace add --name "Demo" --description "Demo workspace" --sample

# Show workspace details
miminions workspace show <workspace_id>

# Evaluate workspace rules
miminions workspace evaluate <workspace_id>
```

## Development Setup

```bash
git clone https://github.com/MiMinions-ai/MiMinions.git
cd MiMinions
pip install -e ".[dev]"
pytest tests/
```

### Running Tests by Layer

```bash
# Unit tests
pytest tests/unit/

# Integration tests
pytest tests/integration/

# End-to-end tests
bash tests/e2e/run_all.sh
```

## Publishing

Build and publish with `uv`:

```bash
uv build
uv publish
```

Build a standalone CLI binary:

```bash
bash deploy/build_cli.sh
```
