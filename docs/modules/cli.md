# CLI & Chat

The `miminions` CLI provides interactive chat, agent management, and workspace operations.

## Chat

```bash
# Start a new chat session
miminions chat start

# Resume a previous session
miminions chat start --session <session_id>

# Type 'exit' to end the session and trigger background memory distillation
```

### Session Resumption

Passing `--session <id>` loads the `.jsonl` transcript from `JsonlSessionStore` and converts it back into native pydantic-ai messages, giving the LLM full conversational context from prior runs.

### Background Distillation

When you exit a chat session, `MemoryDistiller` runs automatically in the background — extracting facts from the transcript and writing them to memory without blocking your terminal.

## Agent Management

```bash
miminions agent list
miminions agent add --name "MyAgent" --description "..."
miminions agent update <id> --name "NewName"
miminions agent remove <id>
miminions agent activate <id>
miminions agent deactivate <id>
miminions agent set-goal <id> --goal "..."
```

## Workspace Management

```bash
miminions workspace list
miminions workspace add --name "My Workspace" --description "..."
miminions workspace add --name "Demo" --description "Demo" --sample
miminions workspace show <id>
miminions workspace update <id> --name "New Name"
miminions workspace remove <id>

# Nodes
miminions workspace add-node <workspace_id> --name "Node" --type agent
miminions workspace connect-nodes <workspace_id> <node1_id> <node2_id>

# State & rules
miminions workspace set-state <workspace_id> --key "priority" --value "high"
miminions workspace evaluate <workspace_id>
```

## Task Management

```bash
miminions task list
miminions task add --name "My Task" --description "..."
miminions task update <id> --status in_progress
miminions task remove <id>
```

## Knowledge Base

```bash
miminions knowledge list
miminions knowledge add --title "Topic" --content "..." --category "general"
miminions knowledge update <id> --content "..."
miminions knowledge remove <id>
```

## Authentication

```bash
miminions auth signin --email user@example.com
miminions auth signout
miminions auth config
miminions auth public  # Enable public access mode
```
