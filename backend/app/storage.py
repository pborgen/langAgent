"""SQLite persistence for session events and ingestion jobs.

Replaces the in-memory dicts so data survives restarts. Thread-safe via
check_same_thread=False (SQLite serialises writes internally).
"""

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB_PATH = Path(__file__).resolve().parent.parent / "data" / "support.db"


class Storage:
    def __init__(self, db_path: str | Path | None = None) -> None:
        path = Path(db_path) if db_path else DEFAULT_DB_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._create_tables()

    # ------------------------------------------------------------------
    # Schema
    # ------------------------------------------------------------------

    def _create_tables(self) -> None:
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS session_events (
                id          INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id  TEXT    NOT NULL,
                customer_id TEXT    NOT NULL,
                user_message    TEXT NOT NULL,
                agent_response  TEXT NOT NULL,
                status      TEXT    NOT NULL,
                route       TEXT    NOT NULL,
                tools_used  TEXT    NOT NULL DEFAULT '[]',
                human_approved INTEGER NOT NULL DEFAULT 0,
                created_at  TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_session_events_session
                ON session_events(session_id);

            CREATE TABLE IF NOT EXISTS ingestion_jobs (
                job_id       TEXT PRIMARY KEY,
                tenant_id    TEXT NOT NULL,
                filename     TEXT NOT NULL,
                content_type TEXT NOT NULL,
                source       TEXT NOT NULL DEFAULT 'dashboard',
                storage_uri  TEXT NOT NULL,
                status       TEXT NOT NULL DEFAULT 'queued',
                error        TEXT,
                created_at   TEXT NOT NULL,
                updated_at   TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_ingestion_jobs_status
                ON ingestion_jobs(status);
        """)
        self._conn.commit()

    # ------------------------------------------------------------------
    # Session events
    # ------------------------------------------------------------------

    def insert_session_event(self, event: dict) -> None:
        self._conn.execute(
            """
            INSERT INTO session_events
                (session_id, customer_id, user_message, agent_response,
                 status, route, tools_used, human_approved, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                event["session_id"],
                event["customer_id"],
                event["user_message"],
                event["agent_response"],
                event["status"],
                event["route"],
                json.dumps(event.get("tools_used", [])),
                int(event.get("human_approved", False)),
                event.get("created_at", datetime.now(timezone.utc).isoformat()),
            ),
        )
        self._conn.commit()

    def get_session_events(self, session_id: str) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM session_events WHERE session_id = ? ORDER BY id",
            (session_id,),
        ).fetchall()
        return [self._row_to_session_event(r) for r in rows]

    def get_all_session_events(self) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM session_events ORDER BY id",
        ).fetchall()
        return [self._row_to_session_event(r) for r in rows]

    @staticmethod
    def _row_to_session_event(row: sqlite3.Row) -> dict:
        return {
            "session_id": row["session_id"],
            "customer_id": row["customer_id"],
            "user_message": row["user_message"],
            "agent_response": row["agent_response"],
            "status": row["status"],
            "route": row["route"],
            "tools_used": json.loads(row["tools_used"]),
            "human_approved": bool(row["human_approved"]),
            "created_at": row["created_at"],
        }

    # ------------------------------------------------------------------
    # Ingestion jobs
    # ------------------------------------------------------------------

    def insert_ingestion_job(self, job: dict) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            """
            INSERT INTO ingestion_jobs
                (job_id, tenant_id, filename, content_type, source,
                 storage_uri, status, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                job["job_id"],
                job["tenant_id"],
                job["filename"],
                job["content_type"],
                job["source"],
                job["storage_uri"],
                job.get("status", "queued"),
                job.get("created_at", now),
                now,
            ),
        )
        self._conn.commit()

    def get_ingestion_job(self, job_id: str) -> dict | None:
        row = self._conn.execute(
            "SELECT * FROM ingestion_jobs WHERE job_id = ?", (job_id,)
        ).fetchone()
        return self._row_to_job(row) if row else None

    def update_job_status(self, job_id: str, status: str, error: str | None = None) -> None:
        now = datetime.now(timezone.utc).isoformat()
        self._conn.execute(
            "UPDATE ingestion_jobs SET status = ?, error = ?, updated_at = ? WHERE job_id = ?",
            (status, error, now, job_id),
        )
        self._conn.commit()

    def get_queued_jobs(self, limit: int = 10) -> list[dict]:
        rows = self._conn.execute(
            "SELECT * FROM ingestion_jobs WHERE status = 'queued' ORDER BY created_at LIMIT ?",
            (limit,),
        ).fetchall()
        return [self._row_to_job(r) for r in rows]

    @staticmethod
    def _row_to_job(row: sqlite3.Row) -> dict:
        return {
            "job_id": row["job_id"],
            "tenant_id": row["tenant_id"],
            "filename": row["filename"],
            "content_type": row["content_type"],
            "source": row["source"],
            "storage_uri": row["storage_uri"],
            "status": row["status"],
            "error": row["error"],
            "created_at": row["created_at"],
            "updated_at": row["updated_at"],
        }

    def close(self) -> None:
        self._conn.close()
