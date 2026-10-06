"""Client API for a persistent local execution instance."""

from __future__ import annotations

import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from dataclasses import replace

from .models import ExecutionRequest, TaskHandle, TERMINAL
from .processes import InstanceLock, alive
from .store import ExecutionStore


def worker_command(home: Path, task_id: str | None = None) -> list[str]:
    if getattr(sys, "frozen", False):
        command = [sys.executable, "_execution-worker"]
    else:
        command = [sys.executable, "-u", "-m", "miminions.execution.worker"]
    command += ["--home", str(home)]
    if task_id is not None:
        command += ["--task", task_id]
    return command


def worker_environment() -> dict[str, str]:
    env = os.environ.copy()
    # Preserve editable/source installations when a child changes cwd.
    paths = [str(Path(p or os.getcwd()).resolve()) for p in sys.path if Path(p or os.getcwd()).is_dir()]
    if env.get("PYTHONPATH"):
        paths.append(env["PYTHONPATH"])
    env["PYTHONPATH"] = os.pathsep.join(paths)
    env["PYTHONUNBUFFERED"] = "1"
    env["PYTHONIOENCODING"] = "utf-8"
    return env


class ExecutionService:
    def __init__(self, home: Path | str | None = None):
        if home is None:
            from miminions.core.paths import get_config_dir
            home = get_config_dir()
        self.store = ExecutionStore(home)

    def status(self) -> dict:
        state = self.store.instance()
        heartbeat = state.get("heartbeat")
        fresh = bool(heartbeat and (datetime.now(timezone.utc) - datetime.fromisoformat(heartbeat)).total_seconds() < 15)
        return {**state, "healthy": bool(state.get("running") and fresh and alive(state.get("pid")))}

    def ensure_instance(self, on_start=None) -> None:
        if self.status().get("healthy"):
            return
        if on_start:
            on_start("Starting local execution instance...")
        deadline = time.monotonic() + 10
        launch_lock = InstanceLock(self.store.home / "execution-start.lock")
        process = None
        try:
            while time.monotonic() < deadline:
                if self.status().get("healthy"):
                    return
                if launch_lock.file is None and launch_lock.acquire():
                    # Another submitter may have finished startup while we acquired the lock.
                    if not self.status().get("healthy"):
                        options = {"start_new_session": True} if os.name != "nt" else {
                            "creationflags": subprocess.DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP |
                            subprocess.CREATE_NO_WINDOW,
                        }
                        with (self.store.home / "execution-instance.log").open("ab") as log:
                            env = worker_environment()
                            if getattr(sys, "frozen", False):
                                # Independent extraction survives the submitting one-file CLI's exit.
                                env["PYINSTALLER_RESET_ENVIRONMENT"] = "1"
                            process = subprocess.Popen(worker_command(self.store.home), stdin=subprocess.DEVNULL,
                                                       stdout=log, stderr=log, env=env, **options)
                if process is not None and process.poll() is not None:
                    # A racing supervisor can lose the instance lock and exit normally.
                    if process.returncode and not self.status().get("healthy"):
                        raise ValueError(f"Execution instance failed to start. Inspect {self.store.home / 'execution-instance.log'}")
                    if not self.status().get("healthy"):
                        # An old instance may still be releasing its lock during shutdown.
                        process = None
                        launch_lock.close()
                time.sleep(0.1)
            raise ValueError(f"Execution instance was not ready within 10 seconds. Inspect {self.store.home / 'execution-instance.log'}")
        finally:
            launch_lock.close()

    def submit(self, request: ExecutionRequest, *, defer_start: bool = False, on_start=None) -> TaskHandle:
        from .handlers import HANDLER_KINDS
        if request.kind not in HANDLER_KINDS:
            raise ValueError(f"Unsupported execution kind: {request.kind}")
        cwd = Path(request.cwd or os.getcwd()).expanduser().resolve()
        if not cwd.is_dir():
            raise ValueError(f"Working directory does not exist: {cwd}")
        request = replace(request, cwd=str(cwd))
        self.ensure_instance(on_start)
        return TaskHandle(self.store.enqueue(request, released=not defer_start, submitter_pid=os.getpid()), self)

    def get(self, task_id: str):
        return self.store.get(task_id)

    def follow(self, task_id: str, after: int = 0):
        if after < 0:
            raise ValueError("Event sequence cannot be negative")
        task = self.get(task_id)
        if task.status not in TERMINAL:
            self.ensure_instance()
        while True:
            events = self.store.events(task_id, after)
            for event in events:
                after = event.sequence
                yield event
            if self.get(task_id).status in TERMINAL:
                # The terminal transaction may have committed between our two reads.
                remaining = self.store.events(task_id, after)
                for event in remaining:
                    after = event.sequence
                    yield event
                return
            if not self.status().get("healthy"):
                self.ensure_instance()
            time.sleep(0.1)

    def cancel(self, task_id: str):
        self.store.cancel(task_id)
        if self.get(task_id).status not in TERMINAL:
            self.ensure_instance()

    def approve(self, task_id: str, request_id: str, allow: bool):
        self.store.approve(task_id, request_id, allow)

    def stop(self, cancel: bool = False):
        if not self.status().get("healthy"):
            return
        self.store.set_instance(stopping=True)
        if cancel:
            for task in self.store.list():
                if task.status not in TERMINAL:
                    self.store.cancel(task.id)
