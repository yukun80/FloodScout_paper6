from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from floodscout.core.models import CrawlTask, TaskStatus


class TaskStateStore:
    def __init__(self, db_path: Path, max_retries: int = 2) -> None:
        self.db_path = db_path
        self.max_retries = max_retries
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    task_id TEXT PRIMARY KEY,
                    city TEXT NOT NULL,
                    keyword TEXT NOT NULL,
                    start_date TEXT NOT NULL,
                    end_date TEXT NOT NULL,
                    status TEXT NOT NULL,
                    retries INTEGER NOT NULL DEFAULT 0,
                    last_error TEXT,
                    updated_at TEXT NOT NULL
                )
                """
            )

    def upsert_tasks(self, tasks: list[CrawlTask]) -> int:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.executemany(
                """
                INSERT INTO tasks(task_id, city, keyword, start_date, end_date, status, retries, updated_at)
                VALUES(?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(task_id) DO UPDATE SET
                    city=excluded.city,
                    keyword=excluded.keyword,
                    start_date=excluded.start_date,
                    end_date=excluded.end_date,
                    updated_at=excluded.updated_at
                """,
                [
                    (
                        t.task_id,
                        t.city,
                        t.keyword,
                        t.start_date,
                        t.end_date,
                        t.status,
                        t.retries,
                        now,
                    )
                    for t in tasks
                ],
            )
        return len(tasks)

    def fetch_pending(self, limit: int) -> list[CrawlTask]:
        with self._connect() as conn:
            rows = conn.execute(
                """
                SELECT * FROM tasks
                WHERE status IN (?, ?) AND retries <= ?
                ORDER BY updated_at ASC
                LIMIT ?
                """,
                (TaskStatus.PENDING, TaskStatus.FAILED, self.max_retries - 1, limit),
            ).fetchall()
        return [
            CrawlTask(
                task_id=r["task_id"],
                city=r["city"],
                keyword=r["keyword"],
                start_date=r["start_date"],
                end_date=r["end_date"],
                status=r["status"],
                retries=r["retries"],
            )
            for r in rows
        ]

    def mark_running(self, task_id: str) -> None:
        self._update_status(task_id, TaskStatus.RUNNING)

    def mark_done(self, task_id: str) -> None:
        self._update_status(task_id, TaskStatus.DONE)

    def mark_failed(self, task_id: str, error: str) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                """
                UPDATE tasks
                SET status=?, retries=retries+1, last_error=?, updated_at=?
                WHERE task_id=?
                """,
                (TaskStatus.FAILED, error[:500], now, task_id),
            )

    def summary(self) -> dict[str, int]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT status, COUNT(*) AS cnt FROM tasks GROUP BY status"
            ).fetchall()
        data = {r["status"]: r["cnt"] for r in rows}
        for key in (TaskStatus.PENDING, TaskStatus.RUNNING, TaskStatus.DONE, TaskStatus.FAILED):
            data.setdefault(key.value, 0)
        return data

    def _update_status(self, task_id: str, status: TaskStatus) -> None:
        now = datetime.now(timezone.utc).isoformat()
        with self._connect() as conn:
            conn.execute(
                "UPDATE tasks SET status=?, updated_at=? WHERE task_id=?",
                (status, now, task_id),
            )
