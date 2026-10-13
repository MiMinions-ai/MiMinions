"""Transactional queue, events, approvals and checkpoints in a local SQLite DB."""

from __future__ import annotations

import json
import sqlite3
import uuid
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .models import ExecutionRequest, ExecutionTask, TaskEvent, TERMINAL


def now() -> str:
    return datetime.now(timezone.utc).isoformat()


def encode(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, default=str)


class ExecutionStore:
    def __init__(self, home: Path | str):
        self.home = Path(home).expanduser().resolve()
        self.home.mkdir(parents=True, exist_ok=True)
        self.path = self.home / "execution.sqlite3"
        with self.connection() as db:
            db.execute("PRAGMA journal_mode=WAL")
            version = db.execute("PRAGMA user_version").fetchone()[0]
            if version not in (0, 1):
                raise ValueError(f"Unsupported execution database version: {version}")
            db.executescript("""
                CREATE TABLE IF NOT EXISTS tasks (
                    id TEXT PRIMARY KEY, request TEXT NOT NULL, session_key TEXT,
                    status TEXT NOT NULL, created_at TEXT NOT NULL, started_at TEXT,
                    ended_at TEXT, result TEXT, error TEXT, cancel_requested INTEGER NOT NULL DEFAULT 0,
                    released INTEGER NOT NULL DEFAULT 1, submitter_pid INTEGER, child_pid INTEGER
                );
                CREATE INDEX IF NOT EXISTS task_queue ON tasks(status, created_at);
                CREATE TABLE IF NOT EXISTS events (
                    task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    sequence INTEGER NOT NULL, timestamp TEXT NOT NULL, type TEXT NOT NULL,
                    data TEXT NOT NULL, PRIMARY KEY(task_id, sequence)
                );
                CREATE TABLE IF NOT EXISTS approvals (
                    id TEXT PRIMARY KEY, task_id TEXT NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
                    prompt TEXT NOT NULL, response INTEGER
                );
                CREATE TABLE IF NOT EXISTS checkpoints (session_key TEXT PRIMARY KEY, messages TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS instance (id INTEGER PRIMARY KEY CHECK(id=1), data TEXT NOT NULL);
                PRAGMA user_version=1;
            """)

    @contextmanager
    def connection(self, write: bool = False):
        db = sqlite3.connect(self.path, timeout=5, isolation_level=None)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        try:
            if write:
                db.execute("BEGIN IMMEDIATE")
            yield db
            if write:
                db.commit()
        except BaseException:
            if write:
                db.rollback()
            raise
        finally:
            db.close()

    def _event(self, db, task_id: str, event_type: str, data: dict) -> None:
        db.execute(
            "INSERT INTO events VALUES (?, (SELECT COALESCE(MAX(sequence),0)+1 FROM events WHERE task_id=?), ?, ?, ?)",
            (task_id, task_id, now(), event_type, encode(data)),
        )

    def enqueue(self, request: ExecutionRequest, *, released: bool = True, submitter_pid: int | None = None) -> str:
        # Validate JSON before changing state; callable/live runtime payloads are forbidden.
        serialized = json.dumps(request.to_dict(), ensure_ascii=False)
        task_id = "exec_" + uuid.uuid4().hex
        with self.connection(True) as db:
            state = db.execute("SELECT data FROM instance WHERE id=1").fetchone()
            if state:
                instance = json.loads(state[0])
                if instance.get("stopping"):
                    raise ValueError("Execution instance is draining. Wait for it to stop before submitting work.")
                if not instance.get("running"):
                    raise ValueError("Execution instance stopped during submission. Submit the operation again.")
            db.execute(
                "INSERT INTO tasks(id,request,session_key,status,created_at,released,submitter_pid) VALUES (?,?,?,'queued',?,?,?)",
                (task_id, serialized, request.session_key, now(), int(released), submitter_pid),
            )
            self._event(db, task_id, "accepted", {"status": "queued", "kind": request.kind})
        return task_id

    def release(self, task_id: str) -> None:
        with self.connection(True) as db:
            db.execute("UPDATE tasks SET released=1 WHERE id=?", (task_id,))

    def unreleased(self) -> list[tuple[str, int | None]]:
        with self.connection() as db:
            return [(r["id"], r["submitter_pid"]) for r in db.execute("SELECT * FROM tasks WHERE released=0 AND status='queued'")]

    def _task(self, row) -> ExecutionTask:
        return ExecutionTask(
            id=row["id"], request=ExecutionRequest.from_dict(json.loads(row["request"])),
            status=row["status"], created_at=row["created_at"], started_at=row["started_at"],
            ended_at=row["ended_at"], result=json.loads(row["result"]) if row["result"] is not None else None,
            error=row["error"], cancel_requested=bool(row["cancel_requested"]),
        )

    def get(self, task_id: str) -> ExecutionTask:
        with self.connection() as db:
            row = db.execute("SELECT * FROM tasks WHERE id=?", (task_id,)).fetchone()
        if row is None:
            raise ValueError(f"Execution task '{task_id}' not found.")
        return self._task(row)

    def list(self) -> list[ExecutionTask]:
        with self.connection() as db:
            return [self._task(row) for row in db.execute("SELECT * FROM tasks ORDER BY created_at, id")]

    def claim(self) -> ExecutionTask | None:
        with self.connection(True) as db:
            # Earlier tasks in a session block later ones, including approval waits.
            row = db.execute("""
                SELECT t.* FROM tasks t WHERE t.status='queued' AND t.released=1
                AND (t.session_key IS NULL OR NOT EXISTS (
                    SELECT 1 FROM tasks other WHERE other.session_key=t.session_key AND other.id!=t.id
                    AND (other.status IN ('running','waiting_for_input') OR
                         (other.status='queued' AND (other.created_at<t.created_at OR
                          (other.created_at=t.created_at AND other.id<t.id))))
                )) ORDER BY t.created_at,t.id LIMIT 1
            """).fetchone()
            if row is None:
                return None
            db.execute("UPDATE tasks SET status='running',started_at=? WHERE id=?", (now(), row["id"]))
            self._event(db, row["id"], "started", {"status": "running"})
        return self.get(row["id"])

    def append(self, task_id: str, event_type: str, data: dict) -> None:
        with self.connection(True) as db:
            row = db.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is not None and row[0] not in TERMINAL:
                self._event(db, task_id, event_type, data)

    def events(self, task_id: str, after: int = 0) -> list[TaskEvent]:
        with self.connection() as db:
            return [TaskEvent(r["task_id"], r["sequence"], r["timestamp"], r["type"], json.loads(r["data"]))
                    for r in db.execute("SELECT * FROM events WHERE task_id=? AND sequence>? ORDER BY sequence", (task_id, after))]

    def finish(self, task_id: str, status: str, *, result: Any = None, error: str | None = None) -> bool:
        if status not in TERMINAL:
            raise ValueError("Expected a terminal task status")
        with self.connection(True) as db:
            row = db.execute("SELECT status,cancel_requested FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None or row["status"] in TERMINAL:
                return False
            if row["cancel_requested"]:
                status, error = "cancelled", None
            db.execute("UPDATE tasks SET status=?,ended_at=?,result=?,error=? WHERE id=?",
                       (status, now(), encode(result), error, task_id))
            self._event(db, task_id, status, {"status": status, "error": error})
        return True

    def cancel(self, task_id: str) -> None:
        with self.connection(True) as db:
            row = db.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise ValueError(f"Execution task '{task_id}' not found.")
            if row[0] in TERMINAL:
                return
            db.execute("UPDATE tasks SET cancel_requested=1 WHERE id=?", (task_id,))
            if row[0] == "queued":
                db.execute("UPDATE tasks SET status='cancelled',ended_at=? WHERE id=?", (now(), task_id))
                self._event(db, task_id, "cancelled", {"status": "cancelled"})
            else:
                self._event(db, task_id, "cancelling", {})

    def request_approval(self, task_id: str, prompt: str) -> str:
        request_id = uuid.uuid4().hex
        with self.connection(True) as db:
            row = db.execute("SELECT status,cancel_requested FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None or row[0] in TERMINAL or row[1]:
                raise InterruptedError("Task cancelled")
            db.execute("INSERT INTO approvals VALUES (?,?,?,NULL)", (request_id, task_id, prompt))
            db.execute("UPDATE tasks SET status='waiting_for_input' WHERE id=?", (task_id,))
            self._event(db, task_id, "approval_requested", {"request_id": request_id, "prompt": prompt})
        return request_id

    def approvals(self, task_id: str) -> list[dict]:
        with self.connection() as db:
            return [dict(r) for r in db.execute("SELECT * FROM approvals WHERE task_id=? AND response IS NULL", (task_id,))]

    def approval_response(self, task_id: str, request_id: str) -> bool | None:
        with self.connection() as db:
            row = db.execute("SELECT response FROM approvals WHERE task_id=? AND id=?", (task_id, request_id)).fetchone()
        if row is None:
            raise ValueError("Approval request not found")
        return None if row[0] is None else bool(row[0])

    def approve(self, task_id: str, request_id: str, allow: bool) -> None:
        with self.connection(True) as db:
            row = db.execute("SELECT status,cancel_requested FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None or row[0] in TERMINAL or row[1]:
                raise ValueError("Task is no longer accepting approvals")
            changed = db.execute("UPDATE approvals SET response=? WHERE task_id=? AND id=? AND response IS NULL",
                                 (int(allow), task_id, request_id)).rowcount
            if not changed:
                raise ValueError("Approval request not found or already answered")
            pending = db.execute("SELECT 1 FROM approvals WHERE task_id=? AND response IS NULL", (task_id,)).fetchone()
            if pending is None:
                db.execute("UPDATE tasks SET status='running' WHERE id=?", (task_id,))
            self._event(db, task_id, "approval_answered", {"request_id": request_id, "allow": allow})

    def checkpoint(self, session_key: str) -> str | None:
        with self.connection() as db:
            row = db.execute("SELECT messages FROM checkpoints WHERE session_key=?", (session_key,)).fetchone()
        return row[0] if row else None

    def save_checkpoint(self, session_key: str, messages: str) -> None:
        with self.connection(True) as db:
            db.execute("INSERT OR REPLACE INTO checkpoints VALUES (?,?)", (session_key, messages))

    def instance(self) -> dict:
        with self.connection() as db:
            row = db.execute("SELECT data FROM instance WHERE id=1").fetchone()
        return json.loads(row[0]) if row else {}

    def set_instance(self, **changes) -> dict:
        with self.connection(True) as db:
            row = db.execute("SELECT data FROM instance WHERE id=1").fetchone()
            value = json.loads(row[0]) if row else {}
            value.update(changes)
            db.execute("INSERT OR REPLACE INTO instance VALUES (1,?)", (encode(value),))
        return value

    def recover(self) -> None:
        for task in self.list():
            if task.status in {"running", "waiting_for_input"}:
                self.finish(task.id, "failed", error="Execution instance stopped unexpectedly. Inspect output before submitting new work.")

    def remove(self, task_id: str) -> None:
        with self.connection(True) as db:
            row = db.execute("SELECT status FROM tasks WHERE id=?", (task_id,)).fetchone()
            if row is None:
                raise ValueError(f"Execution task '{task_id}' not found.")
            if row[0] not in TERMINAL:
                raise ValueError("Cancel the execution task and wait for termination before removing it.")
            db.execute("DELETE FROM tasks WHERE id=?", (task_id,))
