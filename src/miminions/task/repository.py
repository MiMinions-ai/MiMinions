"""
SQLite persistence layer for tasks and task dependencies.

Based on spec 004 research.md SQLite schema design.
"""

import sqlite3
import json
from typing import Optional
from pathlib import Path
from datetime import datetime

from .models import Task, TaskStatus, TaskDependency
from .exceptions import TaskNotFoundError


class TaskRepository:
    """
    Repository for task persistence using SQLite.

    Provides CRUD operations and maps pydantic models to SQLite rows.
    Per spec 004 research.md:174-238.
    """

    def __init__(self, db_path: str | Path = ":memory:"):
        """
        Initialize task repository.

        Args:
            db_path: Path to SQLite database file (default: in-memory)
        """
        self.db_path = str(db_path)
        self._conn: Optional[sqlite3.Connection] = None
        self._init_schema()

    def _get_connection(self) -> sqlite3.Connection:
        """Get or create database connection."""
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._conn.row_factory = sqlite3.Row
            # Enable WAL mode for concurrent access
            self._conn.execute("PRAGMA journal_mode=WAL")
        return self._conn

    def _init_schema(self) -> None:
        """Initialize database schema."""
        conn = self._get_connection()
        cursor = conn.cursor()

        # Tasks table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                priority INTEGER NOT NULL DEFAULT 50,
                status TEXT NOT NULL CHECK(status IN ('pending', 'running', 'completed', 'failed', 'cancelled')),
                assigned_agent_id TEXT,
                input_json TEXT,
                output_json TEXT,
                created_at REAL NOT NULL,
                started_at REAL,
                completed_at REAL,
                timeout_seconds INTEGER,
                retry_count INTEGER NOT NULL DEFAULT 0,
                max_retries INTEGER NOT NULL DEFAULT 0,
                error_message TEXT
            )
        """)

        # Task dependencies table (DAG edges)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS task_dependencies (
                task_id TEXT NOT NULL,
                depends_on_task_id TEXT NOT NULL,
                PRIMARY KEY (task_id, depends_on_task_id),
                FOREIGN KEY (task_id) REFERENCES tasks(task_id) ON DELETE CASCADE,
                FOREIGN KEY (depends_on_task_id) REFERENCES tasks(task_id) ON DELETE CASCADE
            )
        """)

        # Create indexes for query performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_status ON tasks(status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tasks_priority ON tasks(priority DESC)")

        conn.commit()

    def save_task(self, task: Task) -> None:
        """
        Save or update a task.

        Args:
            task: Task to persist
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR REPLACE INTO tasks (
                task_id, name, priority, status, assigned_agent_id,
                input_json, output_json, created_at, started_at, completed_at,
                timeout_seconds, retry_count, max_retries, error_message
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.task_id,
            task.name,
            task.priority,
            task.status.value,
            task.assigned_agent_id,
            json.dumps(task.input_data),
            json.dumps(task.output_data) if task.output_data else None,
            task.created_at.timestamp(),
            task.started_at.timestamp() if task.started_at else None,
            task.completed_at.timestamp() if task.completed_at else None,
            task.timeout_seconds,
            task.retry_count,
            task.max_retries,
            task.error_message
        ))

        conn.commit()

    def load_task(self, task_id: str) -> Task:
        """
        Load a task by ID.

        Args:
            task_id: Task identifier

        Returns:
            Task object

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("SELECT * FROM tasks WHERE task_id = ?", (task_id,))
        row = cursor.fetchone()

        if row is None:
            raise TaskNotFoundError(task_id)

        return self._row_to_task(row)

    def load_all_tasks(self, status: Optional[TaskStatus] = None) -> list[Task]:
        """
        Load all tasks, optionally filtered by status.

        Args:
            status: Filter by task status (None = all tasks)

        Returns:
            List of tasks
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        if status:
            cursor.execute("SELECT * FROM tasks WHERE status = ?", (status.value,))
        else:
            cursor.execute("SELECT * FROM tasks")

        rows = cursor.fetchall()
        return [self._row_to_task(row) for row in rows]

    def delete_task(self, task_id: str) -> None:
        """
        Delete a task and its dependencies.

        Args:
            task_id: Task to delete

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        # Check if task exists
        cursor.execute("SELECT task_id FROM tasks WHERE task_id = ?", (task_id,))
        if cursor.fetchone() is None:
            raise TaskNotFoundError(task_id)

        # Delete task (dependencies cascade)
        cursor.execute("DELETE FROM tasks WHERE task_id = ?", (task_id,))
        conn.commit()

    def save_dependency(self, dependency: TaskDependency) -> None:
        """
        Save a task dependency.

        Args:
            dependency: Dependency to persist
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT OR IGNORE INTO task_dependencies (task_id, depends_on_task_id)
            VALUES (?, ?)
        """, (dependency.task_id, dependency.depends_on_task_id))

        conn.commit()

    def load_dependencies(self, task_id: str) -> list[str]:
        """
        Load all dependencies for a task.

        Args:
            task_id: Task identifier

        Returns:
            List of task IDs this task depends on
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT depends_on_task_id FROM task_dependencies WHERE task_id = ?",
            (task_id,)
        )

        return [row[0] for row in cursor.fetchall()]

    def load_dependents(self, task_id: str) -> list[str]:
        """
        Load all tasks that depend on this task.

        Args:
            task_id: Task identifier

        Returns:
            List of task IDs that depend on this task
        """
        conn = self._get_connection()
        cursor = conn.cursor()

        cursor.execute(
            "SELECT task_id FROM task_dependencies WHERE depends_on_task_id = ?",
            (task_id,)
        )

        return [row[0] for row in cursor.fetchall()]

    def update_status(self, task_id: str, status: TaskStatus, **kwargs) -> None:
        """
        Update task status and optional fields.

        Args:
            task_id: Task to update
            status: New status
            **kwargs: Additional fields to update (e.g., error_message, completed_at)

        Raises:
            TaskNotFoundError: If task doesn't exist
        """
        # Load, update, save pattern
        task = self.load_task(task_id)
        task.status = status

        # Update additional fields
        for key, value in kwargs.items():
            if hasattr(task, key):
                setattr(task, key, value)

        self.save_task(task)

    def close(self) -> None:
        """Close database connection."""
        if self._conn:
            self._conn.close()
            self._conn = None

    def _row_to_task(self, row: sqlite3.Row) -> Task:
        """
        Convert SQLite row to Task object.

        Args:
            row: Database row

        Returns:
            Task object
        """
        return Task(
            task_id=row['task_id'],
            name=row['name'],
            priority=row['priority'],
            status=TaskStatus(row['status']),
            assigned_agent_id=row['assigned_agent_id'],
            input_data=json.loads(row['input_json']) if row['input_json'] else {},
            output_data=json.loads(row['output_json']) if row['output_json'] else None,
            created_at=datetime.fromtimestamp(row['created_at']),
            started_at=datetime.fromtimestamp(row['started_at']) if row['started_at'] else None,
            completed_at=datetime.fromtimestamp(row['completed_at']) if row['completed_at'] else None,
            timeout_seconds=row['timeout_seconds'],
            retry_count=row['retry_count'],
            max_retries=row['max_retries'],
            error_message=row['error_message']
        )

    def __enter__(self):
        """Context manager entry."""
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
