"""
Execution commands for MiMinions CLI.
Handles tool execution, session management, and interaction tracking.
"""

import asyncio
import click
import io
import json
import subprocess
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from .auth import get_config_dir, is_authenticated, is_public_access_enabled
from miminions.agent.simple_agent import Agent
from miminions.tools import GenericTool


# ── File helpers (same pattern as agent.py / task.py) ──────────────────────

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


# ── Auth decorator (mirrors all other CLI modules) ──────────────────────────

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


# ── Agent builder — replays tool_sources for in-session persistency ─────────

def _build_agent(session_id: str, session: dict) -> Agent:
    """
    Reconstruct the session Agent by replaying its persisted tool_sources.
    This gives tools in-memory persistency across CLI calls without a server.
    """
    agent = Agent(name=f"session-{session_id}")
    for src in session.get("tool_sources", []):
        if src["type"] == "module":
            _load_module(agent, src["path"])
    return agent

def _load_module(agent: Agent, path: str) -> int:
    """Load GenericTool instances from a .py file into the agent."""
    import importlib.util
    spec = importlib.util.spec_from_file_location("_mm_tools", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    count = 0
    for name in dir(mod):
        obj = getattr(mod, name)
        if isinstance(obj, GenericTool):
            agent.add_tool(obj)
            count += 1
    return count


# ── Execution context — captures stdout, intercepts stdin ───────────────────

class _Stdin:
    """Intercepts input() calls from tools, records them for the interaction log."""
    def __init__(self):
        self.exchanges = []

    def readline(self) -> str:
        sys.__stdout__.write("\n🔵  Tool requires input: ")
        sys.__stdout__.flush()
        response = sys.__stdin__.readline().rstrip("\n")
        self.exchanges.append({"prompt": "stdin", "response": response})
        return response + "\n"

    def fileno(self): return sys.__stdin__.fileno()
    def isatty(self): return False


def _run_tool(agent: Agent, tool_name: str, inputs: dict, session_id: str) -> None:
    """
    Execute a tool with stdout capture and stdin interception.
    Automatically logs the interaction — no manual call needed.
    """
    buf = io.StringIO()
    stdin = _Stdin()
    old_out, old_in = sys.stdout, sys.stdin
    sys.stdout, sys.stdin = buf, stdin

    start = time.time()
    result, status = None, "success"

    try:
        raw = agent.execute_tool(tool_name, **inputs)
        result = asyncio.run(raw) if asyncio.iscoroutine(raw) else raw
    except RuntimeError as e:
        if "async" in str(e).lower():
            try:
                result = asyncio.run(agent.execute_tool_async(tool_name, **inputs))
            except Exception as inner:
                result, status = str(inner), "error"
        else:
            result, status = str(e), "error"
    except Exception as e:
        result, status = str(e), "error"
    finally:
        sys.stdout, sys.stdin = old_out, old_in

    elapsed = round((time.time() - start) * 1000, 2)
    captured = buf.getvalue()

    # Auto-log every execution
    interactions = _load(_interactions_file()) or []
    interaction_id = str(uuid.uuid4())[:8]
    interactions.append({
        "id": interaction_id,
        "session_id": session_id,
        "tool": tool_name,
        "inputs": inputs,
        "result": result if isinstance(result, (str, int, float, bool, dict, list, type(None))) else str(result),
        "status": status,
        "stdout": captured,
        "user_inputs": stdin.exchanges,
        "elapsed_ms": elapsed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _save(_interactions_file(), interactions)

    # Update session counter
    sessions = _load(_sessions_file())
    if session_id in sessions:
        sessions[session_id]["interaction_count"] = sessions[session_id].get("interaction_count", 0) + 1
        _save(_sessions_file(), sessions)

    # Print results
    if captured:
        click.echo(f"\n── stdout ──\n{captured.rstrip()}\n───────────")
    if stdin.exchanges:
        click.echo(f"   ({len(stdin.exchanges)} user input(s) recorded)")
    if status == "success":
        click.echo(f"✓  {result}  [{elapsed}ms | {interaction_id}]")
    else:
        click.echo(f"✗  {result}", err=True)


# ── CLI ─────────────────────────────────────────────────────────────────────

@click.group()
def execution_cli():
    """Tool execution, session management, and interaction tracking."""
    pass


@execution_cli.command("run")
@click.argument("tool_name")
@click.option("--input", "inputs", multiple=True, metavar="KEY=VALUE", help="Repeatable.")
@require_auth()
def run_tool(tool_name: str, inputs: tuple):
    """Execute a tool in the active session.

    \b
    Example:
        miminions execution run calculator --input operation=add --input a=5 --input b=3
    """
    session_id, session = _active_session()
    if not session_id:
        click.echo("No active session. Run: miminions execution session start", err=True)
        return

    parsed = {}
    for pair in inputs:
        if "=" not in pair:
            click.echo(f"Invalid input '{pair}'. Use KEY=VALUE.", err=True)
            return
        k, _, v = pair.partition("=")
        try:
            parsed[k.strip()] = json.loads(v.strip())
        except json.JSONDecodeError:
            parsed[k.strip()] = v.strip()

    agent = _build_agent(session_id, session)
    if not agent.get_tool(tool_name):
        click.echo(f"Tool '{tool_name}' not found. Available: {', '.join(agent.list_tools()) or 'none'}", err=True)
        return

    _run_tool(agent, tool_name, parsed, session_id)


# ── Session ──────────────────────────────────────────────────────────────────

@execution_cli.group("session")
def session_group():
    """Manage live execution sessions."""
    pass


@session_group.command("start")
@click.option("--name", default=None)
@require_auth()
def start_session(name: Optional[str]):
    """Start a new session."""
    sid, _ = _active_session()
    if sid:
        click.echo(f"Session '{sid}' already active. Stop it first.", err=True)
        return
    session_id = str(uuid.uuid4())[:8]
    sessions = _load(_sessions_file())
    sessions[session_id] = {
        "name": name or f"session-{session_id}",
        "status": "active",
        "started_at": datetime.now(timezone.utc).isoformat(),
        "interaction_count": 0,
        "tool_sources": [],
    }
    _save(_sessions_file(), sessions)
    click.echo(f"✓  Session started  |  ID: {session_id}")
    click.echo(f"   Add tools: miminions execution session add-tool {session_id} ./tools.py")


@session_group.command("stop")
@require_auth()
def stop_session():
    """Stop the active session."""
    session_id, session = _active_session()
    if not session_id:
        click.echo("No active session.", err=True)
        return
    sessions = _load(_sessions_file())
    sessions[session_id]["status"] = "stopped"
    sessions[session_id]["stopped_at"] = datetime.now(timezone.utc).isoformat()
    _save(_sessions_file(), sessions)
    click.echo(f"✓  Session '{session.get('name', session_id)}' stopped.")


@session_group.command("list")
@require_auth()
def list_sessions():
    """List all sessions."""
    sessions = _load(_sessions_file())
    if not sessions:
        click.echo("No sessions found.")
        return
    for sid, s in sessions.items():
        marker = " ◀ active" if s.get("status") == "active" else ""
        click.echo(f"  {sid}  {s.get('name', sid)}  ({s.get('status')})  interactions={s.get('interaction_count', 0)}{marker}")


@session_group.command("add-tool")
@click.argument("session_id")
@click.argument("module_path")
@require_auth()
def add_tool(session_id: str, module_path: str):
    """Register a Python module's tools into a session (persists across runs).

    \b
    Example:
        miminions execution session add-tool abc123 ./my_tools.py
    """
    sessions = _load(_sessions_file())
    if session_id not in sessions:
        click.echo(f"Session '{session_id}' not found.", err=True)
        return
    path = Path(module_path).resolve()
    if not path.exists():
        click.echo(f"File not found: {path}", err=True)
        return
    tmp = Agent(name="tmp")
    try:
        count = _load_module(tmp, str(path))
    except Exception as e:
        click.echo(f"✗  Failed to load: {e}", err=True)
        return
    sessions[session_id]["tool_sources"].append({"type": "module", "path": str(path)})
    _save(_sessions_file(), sessions)
    click.echo(f"✓  {count} tool(s) registered: {', '.join(tmp.list_tools())}")


# ── Interactions ─────────────────────────────────────────────────────────────

@execution_cli.group("interactions")
def interactions_group():
    """View the interaction log."""
    pass


@interactions_group.command("list")
@click.option("--session", default=None)
@click.option("--limit", default=20, show_default=True)
@require_auth()
def list_interactions(session: Optional[str], limit: int):
    """List recorded interactions."""
    items = _load(_interactions_file()) or []
    if session:
        items = [i for i in items if i.get("session_id") == session]
    for r in items[-limit:]:
        flags = ("📄" if r.get("stdout") else "  ") + ("💬" if r.get("user_inputs") else "  ")
        click.echo(f"  {r['id']}  {r['timestamp'][:19]}  {r['tool']:<20}  {r['status']:<8}  {r.get('elapsed_ms', 0):>7.1f}ms  {flags}")


@interactions_group.command("show")
@click.argument("interaction_id")
@require_auth()
def show_interaction(interaction_id: str):
    """Show full details for one interaction."""
    items = _load(_interactions_file()) or []
    record = next((i for i in items if i.get("id") == interaction_id), None)
    if not record:
        click.echo(f"Interaction '{interaction_id}' not found.", err=True)
        return
    click.echo(json.dumps(record, indent=2))


# ── Test runner ───────────────────────────────────────────────────────────────

@execution_cli.command("test")
@click.argument("path", default="tests/")
@click.option("--verbose", "-v", is_flag=True, help="Run pytest with verbose output.")
@click.option("--session", "session_id", default=None, help="Session to log against (defaults to active).")
@require_auth()
def run_tests(path: str, verbose: bool, session_id: Optional[str]):
    """Run pytest on a path and log the result as an interaction.

    \b
    Examples:
        miminions execution test
        miminions execution test tests/test_agent.py
        miminions execution test tests/ --verbose
    """
    if not session_id:
        session_id, _ = _active_session()
    session_id = session_id or "no-session"

    cmd = [sys.executable, "-m", "pytest", path, "--tb=short"]
    if verbose:
        cmd.append("-v")

    click.echo(f"▶  Running tests: {' '.join(cmd)}")
    start = time.time()

    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = round((time.time() - start) * 1000, 2)

    output = proc.stdout + proc.stderr
    status = "success" if proc.returncode == 0 else "error"

    items = _load(_interactions_file()) or []
    interaction_id = str(uuid.uuid4())[:8]
    items.append({
        "id": interaction_id,
        "session_id": session_id,
        "tool": "pytest",
        "inputs": {"path": path, "verbose": verbose},
        "result": f"exit code {proc.returncode}",
        "status": status,
        "stdout": output,
        "user_inputs": [],
        "elapsed_ms": elapsed,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    })
    _save(_interactions_file(), items)

    sessions = _load(_sessions_file())
    if session_id in sessions:
        sessions[session_id]["interaction_count"] = sessions[session_id].get("interaction_count", 0) + 1
        _save(_sessions_file(), sessions)

    click.echo(output.rstrip())
    if status == "success":
        click.echo(f"\n✓  All tests passed  [{elapsed}ms | {interaction_id}]")
    else:
        click.echo(f"\n✗  Tests failed  [{elapsed}ms | {interaction_id}]", err=True)