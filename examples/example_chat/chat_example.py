#!/usr/bin/env python3
"""Standalone example chat script to test the full agent + memory lifecycle.

This script acts like the main CLI but manages a local `_workspace` folder
automatically so you can test LLM reasoning, tool calling, and memory
distillation without needing to configure a global workspace first.
"""

import argparse
import asyncio
import json
import logging
import os
import sys
from pathlib import Path
from typing import Any

from miminions.agent import create_minion
from miminions.core.workspace import Workspace
from miminions.memory import MemoryDistiller, create_llm_filter
from miminions.session.store import JsonlSessionStore


# Configure basic logging to hide HTTP trace spam but show errors
logging.basicConfig(level=logging.WARNING)


def _bootstrap_workspace(root: Path) -> Workspace:
    """Create the test workspace directories and files if they don't exist."""
    root.mkdir(parents=True, exist_ok=True)
    
    # Create required subdirectories
    (root / "prompt").mkdir(exist_ok=True)
    (root / "memory").mkdir(exist_ok=True)
    (root / "sessions").mkdir(exist_ok=True)
    (root / "data").mkdir(exist_ok=True)
    
    # Seed prompt files
    agents_md = root / "prompt" / "AGENTS.md"
    if not agents_md.exists():
        agents_md.write_text(
            "# MiMinions Agent Identity\n\n"
            "You are a helpful, concise AI agent. You have access to tools and "
            "should use them when asked to perform calculations or check capabilities.\n"
        )
        
    user_md = root / "prompt" / "USER.md"
    if not user_md.exists():
        user_md.write_text(
            "# User Preferences\n\n"
            "The user prefers clear, direct answers without unnecessary fluff.\n"
        )
        
    memory_md = root / "memory" / "MEMORY.md"
    if not memory_md.exists():
        memory_md.write_text("# Project Facts\n\n(No facts recorded yet.)\n")

    # Save or load the workspace.json
    workspace_file = root / "workspace.json"
    if workspace_file.exists():
        with open(workspace_file, "r") as f:
            ws_data = json.load(f)
            ws = Workspace.from_dict(ws_data)
    else:
        ws = Workspace()
        ws.name = "Example Chat Test Workspace"
        ws.description = "A local workspace for testing the agent lifecycle."
        ws.root_path = str(root.absolute())
        with open(workspace_file, "w") as f:
            json.dump(ws.to_dict(), f, indent=2)
            
    return ws


def add_numbers(a: int, b: int) -> int:
    """Add two numbers together."""
    return a + b


async def _chat_loop(session_id: str | None) -> None:
    # 1. Setup paths and bootstrap the workspace
    script_dir = Path(__file__).parent.absolute()
    root = script_dir / "_workspace"
    workspace = _bootstrap_workspace(root)
    
    # 2. Setup the session store
    store = JsonlSessionStore(root)
    if not session_id:
        session_id = store.create_session_id()
        
    # 3. Create the Minion and set context
    minion = create_minion(
        name="MiMinionsDemo",
        description="A test agent for verifying the full LLM and memory stack.",
    )
    minion.set_context(workspace, root)
    
    # 4. Register demo tools
    minion.register_tool("add_numbers", "Add two numbers together", add_numbers)
    
    def list_tools() -> list[str]:
        """Return the names of all available tools."""
        return minion.list_tools()
        
    minion.register_tool("list_tools", "List available tools", list_tools)
    
    # 5. Load prior history if resuming
    if hasattr(store, "load_as_pydantic_messages"):
        message_history = store.load_as_pydantic_messages(session_id)
    else:
        message_history = []
        
    print(f"Workspace : {workspace.name}")
    print(f"Session   : {session_id}")
    print("Model     : openai/gpt-oss-20b:free via OpenRouter")
    print("Type 'exit' or 'quit' to end the session.\n")
    
    # 6. Main Chat Loop
    try:
        while True:
            try:
                user_text = input("> ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nSession ended.")
                break

            if not user_text:
                continue

            if user_text.lower() in {"exit", "quit"}:
                print("Session ended.")
                break

            store.append(
                session_id,
                "user",
                user_text,
                meta={"source": "example-chat"},
            )

            try:
                reply = await minion.run(
                    user_text,
                    message_history=message_history,
                )
                message_history = minion._last_messages
            except Exception as exc:
                reply = f"[error] {type(exc).__name__}: {exc}"

            store.append(
                session_id,
                "assistant",
                reply,
                meta={"source": "example-chat"},
            )

            print(f"\n{reply}\n")
    finally:
        # 7. Run distillation on exit
        print("\nRunning memory distillation in the background...")
        try:
            llm_filter = create_llm_filter(minion._model)
            distiller = MemoryDistiller(llm_filter=llm_filter)
            result = distiller.distill_session(
                workspace=workspace,
                root_path=str(root),
                session_id=session_id,
            )
            print(f"Distillation complete! Extracted {result.promoted_counts['tier1']} history, "
                  f"{result.promoted_counts['tier2']} facts, "
                  f"{result.promoted_counts['tier3']} global insights.")
        except Exception as exc:
            print(f"Warning: memory distillation failed: {exc}")


def main():
    parser = argparse.ArgumentParser(description="Run the example MiMinions chat.")
    parser.add_argument(
        "--session", 
        type=str, 
        help="Resume an existing session ID"
    )
    args = parser.add_argument_group()
    args = parser.parse_args()
    
    # Ensure OPENROUTER_API_KEY is loaded if testing locally
    if "OPENROUTER_API_KEY" not in os.environ:
        env_file = Path(__file__).parent.parent.parent / ".env"
        if env_file.exists():
            with open(env_file) as f:
                for line in f:
                    line = line.strip()
                    if line and "=" in line and not line.startswith("#"):
                        k, v = line.split("=", 1)
                        os.environ[k] = v.strip('"\'')
                        
    if "OPENROUTER_API_KEY" not in os.environ:
        print("WARNING: OPENROUTER_API_KEY is not set. LLM calls may fail.")
        
    asyncio.run(_chat_loop(args.session))


if __name__ == "__main__":
    main()
