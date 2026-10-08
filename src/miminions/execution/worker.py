"""Private supervisor/task entry point; also usable by the frozen CLI."""

from __future__ import annotations

import argparse
import asyncio
import codecs
import os
import subprocess
import threading
import time
import uuid
import sys
from pathlib import Path

from .models import TERMINAL
from .processes import InstanceLock, ProcessTree, alive
from .service import worker_command, worker_environment
from .store import ExecutionStore, now


def _capture(pipe, store: ExecutionStore, task_id: str, event_type: str):
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    try:
        while True:
            chunk = os.read(pipe.fileno(), 4096)
            if not chunk:
                break
            text = decoder.decode(chunk)
            if text:
                store.append(task_id, event_type, {"text": text})
        final = decoder.decode(b"", final=True)
        if final:
            store.append(task_id, event_type, {"text": final})
    finally:
        pipe.close()


def supervise(store: ExecutionStore):
    lock = InstanceLock(store.home / "execution-instance.lock")
    if not lock.acquire():
        return
    children = {}
    generation = uuid.uuid4().hex
    try:
        store.recover()
        from miminions.core.persistence import load_json
        config = load_json(store.home / "config.json")
        execution_config = config.get("execution", {})
        capacity = execution_config.get("max_concurrency", 4)
        if not isinstance(capacity, int) or isinstance(capacity, bool) or capacity < 1:
            raise ValueError("execution.max_concurrency must be a positive integer")
        store.set_instance(pid=os.getpid(), generation=generation, heartbeat=now(), running=True,
                           stopping=False, max_concurrency=capacity)
        last_heartbeat = time.monotonic()
        last_queue_heartbeat = time.monotonic()
        while True:
            state = store.instance()
            if time.monotonic() - last_heartbeat >= 1:
                state = store.set_instance(heartbeat=now())
                last_heartbeat = time.monotonic()
            if time.monotonic() - last_queue_heartbeat >= 5:
                for queued in store.list():
                    if queued.status == "queued":
                        store.append(queued.id, "heartbeat", {"status": "queued", "message":
                                     "Task queued; execution instance responsive."})
                last_queue_heartbeat = time.monotonic()
            for task_id, pid in store.unreleased():
                if not alive(pid):
                    store.release(task_id)
            for task_id, entry in list(children.items()):
                process, tree, readers, cancelling = entry
                task = store.get(task_id)
                if task.cancel_requested and cancelling is None:
                    entry[3] = time.monotonic()
                if entry[3] is not None and time.monotonic() - entry[3] >= 5 and process.poll() is None:
                    tree.kill()
                if process.poll() is not None:
                    # Close surviving descendants before joining readers: they may hold pipes open.
                    tree.cleanup_descendants()
                    for reader in readers:
                        reader.join(timeout=5)
                    outcomes = [e.data for e in store.events(task_id) if e.type == "outcome"]
                    if task.cancel_requested:
                        store.finish(task_id, "cancelled")
                    elif outcomes and process.returncode == 0:
                        outcome = outcomes[-1]
                        store.finish(task_id, outcome["status"], result=outcome.get("result"), error=outcome.get("error"))
                    else:
                        store.finish(task_id, "failed", error=f"Task process exited unexpectedly (exit {process.returncode}). Inspect recorded output.")
                    del children[task_id]
            # Draining still launches already accepted queued tasks.
            while len(children) < capacity:
                task = store.claim()
                if task is None:
                    break
                process = None
                tree = None
                try:
                    options = {"start_new_session": True} if os.name != "nt" else {
                        "creationflags": subprocess.CREATE_NEW_PROCESS_GROUP | subprocess.CREATE_NO_WINDOW,
                    }
                    process = subprocess.Popen(worker_command(store.home, task.id), cwd=task.request.cwd or None,
                                               stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                               env=worker_environment(), **options)
                    tree = ProcessTree(process)
                    readers = [threading.Thread(target=_capture, args=(pipe, store, task.id, kind), daemon=True)
                               for pipe, kind in ((process.stdout, "stdout"), (process.stderr, "stderr"))]
                    for reader in readers:
                        reader.start()
                    # Child cannot execute tools until it belongs to the owned process tree.
                    with store.connection(True) as db:
                        db.execute("UPDATE tasks SET child_pid=? WHERE id=?", (process.pid, task.id))
                    children[task.id] = [process, tree, readers, None]
                except Exception as exc:
                    if tree is not None:
                        tree.kill()
                        tree.close()
                    elif process is not None:
                        process.kill()
                    if process is not None:
                        process.wait()
                    store.finish(task.id, "failed", error=f"Failed to launch task: {exc}")
            if state.get("stopping") and not children and not any(t.status == "queued" for t in store.list()):
                break
            time.sleep(0.1)
    finally:
        for task_id, (process, tree, readers, _) in children.items():
            tree.kill()
            process.wait()
            tree.close()
            for reader in readers:
                reader.join(timeout=5)
            store.finish(task_id, "failed", error="Execution instance shut down unexpectedly.")
        state = store.instance()
        if state.get("generation") == generation:
            store.set_instance(running=False, heartbeat=now())
        lock.close()


async def _run_task(store: ExecutionStore, task_id: str):
    from .handlers import TaskContext, get_handler
    task = store.get(task_id)
    context = TaskContext(store, task)
    handler = get_handler(task.request.kind)
    runner = asyncio.create_task(handler(context))
    try:
        while not runner.done():
            if store.get(task_id).cancel_requested:
                runner.cancel()
                break
            await asyncio.sleep(0.1)
        result = await runner
        store.append(task_id, "outcome", {"status": "completed", "result": result})
    except asyncio.CancelledError:
        store.append(task_id, "outcome", {"status": "cancelled"})
    except Exception as exc:
        store.append(task_id, "outcome", {"status": "failed", "error": f"{type(exc).__name__}: {exc}"})
    finally:
        if not runner.done():
            runner.cancel()
            await asyncio.gather(runner, return_exceptions=True)


def execute(store: ExecutionStore, task_id: str):
    # Wait for the supervisor to assign this process to its Windows Job Object.
    deadline = time.monotonic() + 10
    while True:
        with store.connection() as db:
            row = db.execute("SELECT child_pid,status FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None or row["status"] in TERMINAL:
            return
        # A one-file frozen executable has a bootloader PID distinct from this interpreter.
        if row["child_pid"] is not None:
            break
        if time.monotonic() > deadline:
            raise RuntimeError("Supervisor did not authorize task startup")
        time.sleep(0.1)

    owner = store.instance()
    stopped = threading.Event()

    def monitor():
        last_activity = time.monotonic()
        last_sequence = 0
        while not stopped.wait(0.5):
            # POSIX lacks kill-on-owner-close. A watchdog tears down an orphaned task group.
            current_owner = store.instance()
            if current_owner.get("generation") != owner.get("generation") or not alive(owner.get("pid")):
                if os.name != "nt":
                    import signal
                    os.killpg(os.getpgrp(), signal.SIGKILL)
                os._exit(1)
            events = store.events(task_id, last_sequence)
            if events:
                last_sequence = events[-1].sequence
                last_activity = time.monotonic()
            elif time.monotonic() - last_activity >= 5:
                store.append(task_id, "heartbeat", {"status": store.get(task_id).status,
                                                    "message": "Task process responsive; waiting for output."})
                last_activity = time.monotonic()

    watcher = threading.Thread(target=monitor, daemon=True)
    watcher.start()
    class EventWriter:
        """Python writes commit synchronously; raw descriptor writes still use capture pipes."""
        def __init__(self, stream, original):
            self.stream = stream
            self.original = original

        def write(self, text):
            if text:
                store.append(task_id, self.stream, {"text": text})
            return len(text)

        def flush(self):
            pass

        def __getattr__(self, name):
            return getattr(self.original, name)

    original_stdout, original_stderr = sys.stdout, sys.stderr
    sys.stdout = EventWriter("stdout", original_stdout)
    sys.stderr = EventWriter("stderr", original_stderr)
    try:
        asyncio.run(_run_task(store, task_id))
    finally:
        sys.stdout, sys.stderr = original_stdout, original_stderr
        stopped.set()
        watcher.join(timeout=1)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Private MiMinions execution worker")
    parser.add_argument("--home", required=True)
    parser.add_argument("--task")
    args = parser.parse_args(argv)
    os.environ["MIMINIONS_HOME"] = str(Path(args.home).resolve())
    store = ExecutionStore(args.home)
    if args.task:
        execute(store, args.task)
    else:
        supervise(store)


if __name__ == "__main__":
    main()
