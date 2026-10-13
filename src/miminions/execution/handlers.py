"""Reusable command handlers. Heavy runtime imports occur only inside tasks."""

from __future__ import annotations

import asyncio
import time
from dataclasses import dataclass

from .models import ExecutionTask, conversation_key
from .store import ExecutionStore

@dataclass
class TaskContext:
    store: ExecutionStore
    task: ExecutionTask

    @property
    def params(self):
        return self.task.request.params

    def emit(self, kind, **data):
        self.store.append(self.task.id, kind, data)

    def phase(self, message):
        self.emit("phase", message=message)

    def approval(self, prompt: str) -> bool:
        request_id = self.store.request_approval(self.task.id, prompt)
        while True:
            task = self.store.get(self.task.id)
            if task.cancel_requested or task.status in {"cancelled", "failed"}:
                raise InterruptedError("Task cancelled while awaiting approval")
            response = self.store.approval_response(self.task.id, request_id)
            if response is not None:
                return response
            time.sleep(0.1)

    def wire(self, minion):
        minion._on_tool_call = lambda name, args: self.emit("tool_call", name=name, arguments=args)
        minion._on_turn_end = lambda usage, latency: self.emit(
            "turn_end", input_tokens=usage.input_tokens, output_tokens=usage.output_tokens,
            tool_calls=usage.tool_calls, latency=latency)
        return minion

async def _stream(context, minion, prompt, history=None):
    """Retry only before any output or tool activity; never repeat side effects."""
    from miminions.agent.agent import _is_retryable_error
    output = []
    attempt = 0
    original_hook = minion._on_tool_call
    tool_called = False

    def tool_hook(name, args):
        nonlocal tool_called
        tool_called = True
        if original_hook:
            original_hook(name, args)

    minion._on_tool_call = tool_hook
    while True:
        try:
            async for delta in minion.run_stream(prompt, message_history=history):
                output.append(delta)
                context.emit("text_delta", text=delta)
            context.emit("stdout", text="\n")
            return "".join(output)
        except Exception as exc:
            if output or tool_called or attempt >= minion._max_retries or not _is_retryable_error(exc):
                raise
            delay = minion._retry_base_delay * (2 ** attempt)
            attempt += 1
            context.emit("retry", message=f"Provider request failed; retrying in {delay:.1f}s (attempt {attempt}).")
            await asyncio.sleep(delay)


def _append_once(store, session_id, role, content, task_id, **meta):
    if not any(r.get("role") == role and r.get("meta", {}).get("task_id") == task_id
               for r in store.iter_messages(session_id)):
        store.append(session_id, role, content, meta={**meta, "task_id": task_id})


async def _prompt(context: TaskContext):
    from miminions.agent import create_minion
    from miminions.core.workspace import WorkspaceManager, ensure_workspace
    from miminions.session.store import JsonlSessionStore, trim_message_history
    from pydantic_ai.messages import ModelMessagesTypeAdapter
    from .processes import InstanceLock
    context.phase("Resolving workspace and context...")
    params = context.params
    is_chat = context.task.request.kind == "chat_turn"
    with InstanceLock(context.store.home / "execution-workspace.lock"):
        workspace, root = ensure_workspace(WorkspaceManager(context.store.home), params["workspace"],
                                           create_missing=not is_chat, init_files=not is_chat)
    store = JsonlSessionStore(root)
    session_id = params["session_id"]
    session_key = context.task.request.session_key or conversation_key(workspace.id, session_id)
    checkpoint = context.store.checkpoint(session_key)
    history = ModelMessagesTypeAdapter.validate_json(checkpoint) if checkpoint else store.load_as_pydantic_messages(session_id)
    history = trim_message_history(history)
    meta = {"source": "cli-chat" if is_chat else "cli-prompt", "workspace_id": workspace.id}
    _append_once(store, session_id, "user", params["prompt"], context.task.id, **meta)
    minion = None
    reply = ""
    try:
        minion = context.wire(create_minion(name="MiMinions", description=f"MiMinions agent for workspace '{workspace.name}'."))
        minion.set_context(workspace, root)
        context.phase("Requesting model response...")
        reply = await _stream(context, minion, params["prompt"], history)
        context.store.save_checkpoint(session_key, ModelMessagesTypeAdapter.dump_json(minion._last_messages).decode("utf-8"))
        return reply
    except BaseException as exc:
        partial = "".join(e.data["text"] for e in context.store.events(context.task.id) if e.type == "text_delta")
        reply = "\n".join(filter(None, [partial, f"[error] {type(exc).__name__}: {exc}"]))
        meta["error"] = True
        raise
    finally:
        _append_once(store, session_id, "assistant", reply, context.task.id, **meta)
        if minion is not None:
            await minion.cleanup(rebuild=False)


async def _agent(context: TaskContext):
    from miminions.cli.agent import _build_cli_extension_agent
    from mcp import StdioServerParameters
    params = context.params
    context.phase("Building saved-agent runtime...")
    minion = context.wire(_build_cli_extension_agent(params["agent"]))
    try:
        for name, config in params["agent"].get("mcp_servers", {}).items():
            context.phase(f"Connecting MCP server '{name}'...")
            await minion.connect_mcp_server(name, StdioServerParameters(command=config["command"], args=list(config.get("args", []))))
            await minion.load_tools_from_mcp_server(name)
        if context.task.request.kind == "agent_tool":
            context.emit("tool_call", name=params["tool_name"], arguments=params["arguments"])
            result = await minion.execute_async(params["tool_name"], arguments=params["arguments"])
            if result.error:
                raise RuntimeError(result.error)
            context.emit("stdout", text=f"Tool: {result.tool_name}\nStatus: {result.status.value}\nResult: {result.result}\n"
                         f"Execution time (ms): {result.execution_time_ms:.2f}\n")
            return result.result
        context.phase("Requesting model response...")
        return await _stream(context, minion, params["prompt"])
    finally:
        await minion.cleanup(rebuild=False)


async def _session_tool(context: TaskContext):
    from miminions.cli.execution import _build_agent, _record_interaction
    from datetime import datetime, timezone
    params = context.params
    context.phase("Loading execution-session tools...")
    agent = context.wire(_build_agent(params["session_id"], params["session"]))
    started = datetime.now(timezone.utc)
    result = None
    error = None
    try:
        context.emit("tool_call", name=params["tool_name"], arguments=params["inputs"])
        result = await agent.execute_tool_async(params["tool_name"], **params["inputs"])
        context.emit("stdout", text=f"Result: {result}\n", source="result")
        return result
    except BaseException as exc:
        error = f"{type(exc).__name__}: {exc}"
        raise
    finally:
        await agent.cleanup(rebuild=False)
        output = "".join(e.data["text"] for e in context.store.events(context.task.id)
                         if e.type == "stdout" and e.data.get("source") != "result")
        workflow = _record_interaction(params["session_id"], f"session-{params['session_id']}",
                                       f"Execute tool: {params['tool_name']}", params["tool_name"], params["inputs"],
                                       result, error, "error" if error else "success",
                                       (datetime.now(timezone.utc) - started).total_seconds() * 1000, output)
        context.emit("phase", message=f"Recorded as WorkflowRun {workflow.id}")


async def _tool_test(context: TaskContext):
    from miminions.cli.execution import _build_agent, _load, _save, _interactions_file
    from miminions.workflow.models import WorkflowTrace, WorkflowRun, AgentRunRecord
    from .processes import InstanceLock
    params = context.params
    agent = context.wire(_build_agent(params["session_id"], params["session"]))
    trace = WorkflowTrace()
    outputs = []
    errors = []
    try:
        names = agent.list_tools()
        context.phase(f"Testing {len(names)} tool(s)...")
        for name in names:
            info = agent.get_tool_info(name) or {}
            arguments = {key: value["default"] for key, value in info.get("parameters", {}).get("properties", {}).items()
                         if "default" in value}
            start = time.monotonic()
            result = None
            error = None
            try:
                context.emit("tool_call", name=name, arguments=arguments)
                result = await agent.execute_tool_async(name, **arguments)
            except Exception as exc:
                error = f"{type(exc).__name__}: {exc}"
                errors.append(error)
            trace.add_tool_record(tool_name=name, kwargs=arguments, result=result, error=error,
                                  status="error" if error else "success", execution_time_ms=(time.monotonic()-start)*1000)
            outputs.append(f"{name}: {error if error else result}")
            context.emit("stdout", text=outputs[-1] + "\n")
        trace.add_agent_record(AgentRunRecord(prompt=params["prompt"], output=" | ".join(outputs)))
        workflow = WorkflowRun(agent_name=f"session-{params['session_id']}", trace=trace)
        with InstanceLock(context.store.home / "execution-interactions.lock"):
            interactions = _load(_interactions_file())
            interactions.setdefault(params["session_id"], []).append(workflow.to_dict())
            _save(_interactions_file(), interactions)
        context.phase(f"Recorded as WorkflowRun {workflow.id}")
        if errors:
            raise RuntimeError(f"{len(errors)} tool test(s) failed")
        return outputs
    finally:
        await agent.cleanup(rebuild=False)


async def _distill(context: TaskContext):
    from miminions.cli.chat import _run_session_distillation
    from miminions.core.workspace import WorkspaceManager, ensure_workspace
    from miminions.agent import create_minion
    context.phase("Distilling session memory...")
    workspace, root = ensure_workspace(WorkspaceManager(context.store.home), context.params["workspace"])
    agent = context.wire(create_minion(name="Session distiller"))
    try:
        await asyncio.to_thread(_run_session_distillation, workspace, root, context.params["session_id"], agent._model)
    finally:
        await agent.cleanup(rebuild=False)


_HANDLERS = {"prompt": _prompt, "chat_turn": _prompt, "agent_ask": _agent, "agent_run": _agent,
             "agent_tool": _agent, "session_tool": _session_tool, "tool_test": _tool_test, "session_distill": _distill}
HANDLER_KINDS = frozenset(_HANDLERS)


def get_handler(kind):
    try:
        handler = _HANDLERS[kind]
    except KeyError as exc:
        raise ValueError(f"Unsupported execution kind: {kind}") from exc

    async def execute(context):
        from miminions.tools.default import command_callbacks
        with command_callbacks(context.approval, lambda stream, text: context.emit(stream, text=text)):
            return await handler(context)

    return execute
