# MiMinions

A Python package for MiMinions - An agentic framework for multi-agent use with a powerful CLI interface.

## Installation

You can install MiMinions using pip:

```bash
pip install miminions
```

## CLI Usage

MiMinions provides a comprehensive command-line interface for managing AI agents, tasks, workflows, and knowledge.

### Authentication

Before using most CLI commands, you need to sign in:

```bash
# Sign in
miminions auth signin --username your_username --password your_password

# Sign in with custom timeout (useful for slow networks)
miminions auth signin --username your_username --password your_password --timeout 60

# Check authentication status
miminions auth status

# Sign out
miminions auth signout
```

#### Public Access Mode

MiMinions supports a public access mode that allows you to use basic CLI functionality without authentication:

```bash
# Enable public access mode
miminions auth config --public-access true

# Disable public access mode
miminions auth config --public-access false

# Configure authentication timeout (minimum 5 seconds)
miminions auth config --auth-timeout 60

# View current configuration
miminions auth config
```

When public access is enabled, CLI commands will show a warning but allow basic functionality without requiring authentication. This is useful for testing or when authentication servers are unavailable.

### Agent Management

Manage AI agents with the following commands:

```bash
# List all agents
miminions agent list

# Add a new agent
miminions agent add --name "My Agent" --description "Agent description" --type "general"

# Update an agent
miminions agent update agent_id --name "New Name" --description "New description"

# Set a goal for an agent
miminions agent set-goal agent_id --goal "Complete the task"

# Run an agent
miminions agent run agent_id

# Run an agent asynchronously
miminions agent run agent_id --async

# Remove an agent
miminions agent remove agent_id
```

### Task Management

Manage tasks with priorities and assignments:

```bash
# List all tasks
miminions task list

# Add a new task
miminions task add --title "My Task" --description "Task description" --priority "high" --agent "agent_id"

# Update a task
miminions task update task_id --title "Updated Title" --status "in_progress"

# Show task details
miminions task show task_id

# Duplicate a task
miminions task duplicate task_id --title "Duplicated Task"

# Remove a task
miminions task remove task_id
```

### Workflow Management

Manage workflows with multiple agents:

```bash
# List all workflows
miminions workflow list

# Add a new workflow
miminions workflow add --name "My Workflow" --description "Workflow description" --agents "agent1,agent2"

# Update a workflow
miminions workflow update workflow_id --name "Updated Workflow"

# Show workflow details
miminions workflow show workflow_id

# Start a workflow
miminions workflow start workflow_id

# Pause a workflow
miminions workflow pause workflow_id

# Stop a workflow
miminions workflow stop workflow_id

# Remove a workflow
miminions workflow remove workflow_id
```

### Knowledge Management

Manage knowledge with versioning and customization:

```bash
# List all knowledge entries
miminions knowledge list

# Add a new knowledge entry
miminions knowledge add --title "My Knowledge" --content "Knowledge content" --category "general" --tags "tag1,tag2"

# Update a knowledge entry (creates new version)
miminions knowledge update entry_id --title "Updated Title" --content "Updated content"

# Show knowledge details
miminions knowledge show entry_id

# Show version history
miminions knowledge version entry_id

# Revert to a previous version
miminions knowledge revert entry_id --version "1.0"

# Customize knowledge format
miminions knowledge customize entry_id --format "markdown"

# Remove a knowledge entry
miminions knowledge remove entry_id
```

### Getting Help

Get help for any command:

```bash
# General help
miminions --help

# Help for a specific command group
miminions agent --help

# Help for a specific command
miminions agent add --help
```

## Development

To set up the development environment:

1. Clone the repository
2. Install development dependencies:
   ```bash
   pip install -e ".[dev]"
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

Data is stored locally in JSON files in the `~/.miminions/` directory.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

