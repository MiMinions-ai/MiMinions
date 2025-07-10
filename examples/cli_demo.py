#!/usr/bin/env python3
"""
Example script demonstrating MiMinions CLI usage.
"""

import subprocess
import sys
import time


def run_command(cmd, description=""):
    """Run a CLI command and display the result."""
    print(f"\n{'='*60}")
    print(f"Running: {' '.join(cmd)}")
    if description:
        print(f"Description: {description}")
    print(f"{'='*60}")
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, check=False)
        print(f"Exit code: {result.returncode}")
        if result.stdout:
            print("Output:")
            print(result.stdout)
        if result.stderr:
            print("Error:")
            print(result.stderr)
    except Exception as e:
        print(f"Error running command: {e}")
    
    time.sleep(1)  # Brief pause for readability


def main():
    """Demonstrate CLI functionality."""
    print("MiMinions CLI Demonstration")
    print("This script demonstrates the key features of the MiMinions CLI")
    
    # Base CLI command
    cli_cmd = [sys.executable, '-m', 'interface.cli.main']
    
    # 1. Show help
    run_command(cli_cmd + ['--help'], "Show general help")
    
    # 2. Check authentication status
    run_command(cli_cmd + ['auth', 'status'], "Check authentication status")
    
    # 3. Sign in
    run_command(cli_cmd + ['auth', 'signin', '--username', 'demo_user', '--password', 'demo_pass'], 
                "Sign in with demo credentials")
    
    # 4. Check authentication status after signin
    run_command(cli_cmd + ['auth', 'status'], "Check authentication status after signin")
    
    # 5. List agents (should be empty)
    run_command(cli_cmd + ['agent', 'list'], "List all agents (should be empty)")
    
    # 6. Add an agent
    run_command(cli_cmd + ['agent', 'add', '--name', 'Demo Agent', '--description', 'A demonstration agent', '--type', 'general'], 
                "Add a new agent")
    
    # 7. List agents (should show the new agent)
    run_command(cli_cmd + ['agent', 'list'], "List all agents (should show Demo Agent)")
    
    # 8. Set a goal for the agent
    run_command(cli_cmd + ['agent', 'set-goal', 'demo_agent', '--goal', 'Demonstrate CLI functionality'], 
                "Set a goal for the demo agent")
    
    # 9. Add a task
    run_command(cli_cmd + ['task', 'add', '--title', 'Demo Task', '--description', 'A demonstration task', '--priority', 'high', '--agent', 'demo_agent'], 
                "Add a new task")
    
    # 10. List tasks
    run_command(cli_cmd + ['task', 'list'], "List all tasks")
    
    # 11. Add a workflow
    run_command(cli_cmd + ['workflow', 'add', '--name', 'Demo Workflow', '--description', 'A demonstration workflow', '--agents', 'demo_agent'], 
                "Add a new workflow")
    
    # 12. List workflows
    run_command(cli_cmd + ['workflow', 'list'], "List all workflows")
    
    # 13. Add knowledge
    run_command(cli_cmd + ['knowledge', 'add', '--title', 'Demo Knowledge', '--content', 'This is demonstration knowledge content', '--category', 'demo', '--tags', 'demo,example'], 
                "Add a new knowledge entry")
    
    # 14. List knowledge
    run_command(cli_cmd + ['knowledge', 'list'], "List all knowledge entries")
    
    # 15. Show help for a specific command
    run_command(cli_cmd + ['agent', '--help'], "Show help for agent commands")
    
    print(f"\n{'='*60}")
    print("Demonstration complete!")
    print("The CLI provides comprehensive management of agents, tasks, workflows, and knowledge.")
    print("All data is stored locally in JSON files in the ~/.miminions/ directory.")
    print(f"{'='*60}")


if __name__ == "__main__":
    main()