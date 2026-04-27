"""
Execution commands for MiMinions CLI.
Handles tool execution, session management, and interaction tracking.

Interaction records are persisted as WorkflowRun objects (from miminions.workflow.models),
ensuring consistency with the workflow tracing layer introduced in PR #46.
"""

import asyncio
import click
import io
import json
import sys
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .auth import get_config_dir, is_authenticated, is_public_access_enabled
from miminions.agent.simple_agent import Agent
from miminions.tools import GenericTool
from miminions.workflow.models import AgentRunRecord, WorkflowRun


# ── File helpers ──────────────────────────────────────────────────────────────

def _sessions_file() -> Path:
    return get_config_dir() / "sessions.json"

def _interactions_file() -> Path:
    return get_config_dir() / "interactions.json"

def _load(path: Path) -> Any:
    return json.loads(path.read_text()) if path.exists() else {}

def _save(path: Path, data: Any) -> None:
    path.write_text(json.dumps(data, indent=2))

def _active_session():
    """Return (id, session) for the current active session, else (None, None)."""
    for sid, s in _load(_sessions_file()).items():
        if s.get("status") == "active":
            return sid, s
    return None, None


# ── Auth decorator ────────────────────────────────────────────────────────────

def require_auth():
    def decorator(f):
        def wrapper(*args, **kwargs):
            if not is_authenticated():
                if is_public_access_enabled():
                    click.echo("⚠️  Public access mode.", err=True)
                else:
                    click.echo("Please sign in first using 'miminions auth signin'", err=True)
                    return
            return f(*args, **kwargs)
        return wrapper
    return decorator


# ── Agent builder ─────────────────────────────────────────────────────────────

def _build_agent(session_id: str, session: dict) -> Agent:
    """Reconstruct the session Agent by replaying its persisted tool_sources."""
    agent = Agent(name=f"session-{session_id}")
    for src in session.get("tool_sources", []):
        if src["type"] == "module":
            _load_module(agent, src["path"])
    return agent

def _load_module(agent: Agent, path: str) -> int:
    """Load GenericTool instances from a .py file into the agent."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_dyn_module", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    count = 0
    for attr in vars(mod).values():
        if isinstance(attr, GenericTool):
            agent.register_tool(attr)
            count += 1
    return count


# ── Interaction recording (uses WorkflowRun from PR #46 models) ───────────────

def _record_interaction(
    session_id: str,
    agent_name: str,
    prompt: str,
    tool_name: str,
    inputs: dict,
    result: Any,
    error: Optional[str],
    status: str,
    execution_time_ms: Optional[float],
    stdout_output: str,
) -> WorkflowRun:
    """
    Record a tool execution as a WorkflowRun and persist it to interactions.json.

    Uses AgentRunRecord + ToolCallRecord from miminions.workflow.models so that
    the CLI interaction log shares the same schema as the workflow tracing layer.
    stdout_output is stored in the ToolCallRecord's kwargs for full reproducibility.
    """
    run = AgentRunRecord(prompt=prompt)
    run.record_tool_call(
        tool_name=tool_name,
        kwargs={**inputs, "__stdout__": stdout_output},
        result=result,
        error=error,
        status=status,
        execution_time_ms=execution_time_ms,
    )
    run.output = stdout_output or str(result)

    workflow_run = WorkflowRun(agent_name=agent_name, run=run)

    # Persist
    interactions = _load(_interactions_file())
    if session_id not in interactions:
        interactions[session_id] = []
    interactions[session_id].append(workflow_run.to_dict())
    _save(_interactions_file(), interactions)

    return workflow_run


# ── Tool execution ────────────────────────────────────────────────────────────

def _run_tool(session_id: str, session: dict, tool_name: str, inputs: dict):
    """Execute a tool and record the result as a WorkflowRun."""
    agent = _build_agent(session_id, session)
    agent_name = f"session-{session_id}"

    buf = io.StringIO()
    old_stdout = sys.stdout
    sys.stdout = buf
    start = datetime.now(timezone.utc)
    result_val = None
    error_val = None
    status = "success"

    try:
        result_obj = asyncio.get_event_loop().run_until_complete(
            agent.execute_async(tool_name, arguments=inputs)
        )
        result_val = result_obj.result
        error_val = result_obj.error
        status = str(result_obj.status)
    except Exception as e:
        error_val = str(e)
        status = "error"
    finally:
        sys.stdout = old_stdout

    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    stdout_output = buf.getvalue()

    workflow_run = _record_interaction(
        session_id=session_id,
        agent_name=agent_name,
        prompt=f"Execute tool: {tool_name}",
        tool_name=tool_name,
        inputs=inputs,
        result=result_val,
        error=error_val,
        status=status,
        execution_time_ms=elapsed_ms,
        stdout_output=stdout_output,
    )

    return workflow_run, stdout_output


# ── CLI command group ─────────────────────────────────────────────────────────

@click.group()
def execution():
    """Manage live execution sessions and tool runs."""
    pass


# ── Session commands ──────────────────────────────────────────────────────────

@execution.group()
def session():
    """Manage execution sessions."""
    pass


@session.command("start")
@click.option("--name", default=None, help="Optional session name.")
def session_start(name):
    """Start a new execution session."""
    sid, existing = _active_session()
    if sid:
        click.echo(f"Session {sid} is already active. Stop it first.")
        return

    session_id = uuid.uuid4().hex[:8]
    sessions = _load(_sessions_file())
    sessions[session_id] = {
        "name": name or session_id,
        "status": "active",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "tool_sources": [],
    }
    _save(_sessions_file(), sessions)
    click.echo(f"Session started: {session_id}")


@session.command("stop")
def session_stop():
    """Stop the active session."""
    sid, s = _active_session()
    if not sid:
        click.echo("No active session.")
        return
    sessions = _load(_sessions_file())
    sessions[sid]["status"] = "stopped"
    sessions[sid]["stopped_at"] = datetime.now(timezone.utc).isoformat()
    _save(_sessions_file(), sessions)
    click.echo(f"Session {sid} stopped.")


@session.command("list")
def session_list():
    """List all sessions."""
    sessions = _load(_sessions_file())
    if not sessions:
        click.echo("No sessions found.")
        return
    for sid, s in sessions.items():
        click.echo(f"[{s['status']}] {sid}  name={s.get('name')}  created={s.get('created_at')}")


# ── Add-tool command ──────────────────────────────────────────────────────────

@execution.command("add-tool")
@click.argument("path")
def add_tool(path):
    """Register a tool module (.py) with the active session."""
    sid, s = _active_session()
    if not sid:
        click.echo("No active session. Run 'execution session start' first.")
        return

    resolved = str(Path(path).resolve())
    sessions = _load(_sessions_file())
    sources = sessions[sid].setdefault("tool_sources", [])

    if any(src["path"] == resolved for src in sources):
        click.echo(f"Tool source already registered: {resolved}")
        return

    # Verify it loads
    agent = Agent(name="probe")
    count = _load_module(agent, resolved)
    sources.append({"type": "module", "path": resolved})
    _save(_sessions_file(), sessions)
    click.echo(f"Registered {count} tool(s) from {resolved}")


# ── Run command ───────────────────────────────────────────────────────────────

@execution.command("run")
@click.argument("tool_name")
@click.option("--input", "inputs", multiple=True, metavar="KEY=VALUE",
              help="Tool input as KEY=VALUE pairs.")
def run_tool(tool_name, inputs):
    """Execute a tool in the active session."""
    sid, s = _active_session()
    if not sid:
        click.echo("No active session.")
        return

    parsed = {}
    for item in inputs:
        if "=" not in item:
            click.echo(f"Invalid input format '{item}'. Use KEY=VALUE.")
            return
        k, v = item.split("=", 1)
        parsed[k.strip()] = v.strip()

    workflow_run, stdout_output = _run_tool(sid, s, tool_name, parsed)
    tool_call = workflow_run.run.tool_calls[0]

    if stdout_output:
        click.echo(stdout_output, nl=False)

    if tool_call.error:
        click.echo(f"Error: {tool_call.error}", err=True)
    else:
        click.echo(f"Result: {tool_call.result}")

    click.echo(f"Recorded as WorkflowRun {workflow_run.id} ({tool_call.execution_time_ms:.1f}ms)")


# ── Interaction commands ──────────────────────────────────────────────────────

@execution.group()
def interaction():
    """View recorded interactions (stored as WorkflowRun objects)."""
    pass


@interaction.command("list")
@click.option("--session-id", default=None, help="Session ID (defaults to active session).")
def interaction_list(session_id):
    """List all recorded WorkflowRuns for a session."""
    if not session_id:
        session_id, _ = _active_session()
    if not session_id:
        click.echo("No active session and no --session-id provided.")
        return

    interactions = _load(_interactions_file())
    runs = interactions.get(session_id, [])
    if not runs:
        click.echo("No interactions recorded.")
        return

    for i, wf_dict in enumerate(runs):
        wf = WorkflowRun.from_dict(wf_dict)
        tc = wf.run.tool_calls[0] if wf.run.tool_calls else None
        tool_name = tc.tool_name if tc else "?"
        status = tc.status if tc else "?"
        click.echo(f"[{i}] {wf.id}  tool={tool_name}  status={status}  created={wf.created_at}")


@interaction.command("show")
@click.argument("index", type=int)
@click.option("--session-id", default=None, help="Session ID (defaults to active session).")
def interaction_show(index, session_id):
    """Show full details of a recorded WorkflowRun by index."""
    if not session_id:
        session_id, _ = _active_session()
    if not session_id:
        click.echo("No active session and no --session-id provided.")
        return

    interactions = _load(_interactions_file())
    runs = interactions.get(session_id, [])

    if index < 0 or index >= len(runs):
        click.echo(f"No interaction at index {index}.")
        return

    wf = WorkflowRun.from_dict(runs[index])
    click.echo(json.dumps(wf.to_dict(), indent=2))


# ── Test runner command ───────────────────────────────────────────────────────

@execution.command("test")
@click.argument("path", default=".")
def run_tests(path):
    """Run pytest and record the result as a WorkflowRun interaction."""
    import subprocess
    sid, s = _active_session()

    start = datetime.now(timezone.utc)
    proc = subprocess.run(
        ["pytest", path, "-v"],
        capture_output=True,
        text=True,
    )
    elapsed_ms = (datetime.now(timezone.utc) - start).total_seconds() * 1000
    passed = proc.returncode == 0
    click.echo(proc.stdout)

    if sid:
        run = AgentRunRecord(prompt=f"pytest {path}")
        run.record_tool_call(
            tool_name="pytest",
            kwargs={"path": path},
            result=proc.stdout,
            error=proc.stderr if not passed else None,
            status="success" if passed else "failure",
            execution_time_ms=elapsed_ms,
        )
        run.output = "Tests passed." if passed else "Tests failed."
        wf = WorkflowRun(agent_name=f"session-{sid}", run=run)

        interactions = _load(_interactions_file())
        interactions.setdefault(sid, []).append(wf.to_dict())
        _save(_interactions_file(), interactions)

        click.echo(f"Recorded as WorkflowRun {wf.id}")


# ── Alias for main.py import ──────────────────────────────────────────────────

execution_cli = execution
