from __future__ import annotations

import json
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Iterable, List

from .models import EventRecord, RegistryEntry, RegistrySnapshot, SessionLog, TestResult


class Storage:
    """Durable SQLite-backed store for sessions, events, and registry state."""

    def __init__(self, db_path: str | None = None) -> None:
        data_dir = Path(__file__).resolve().parent / "data"
        data_dir.mkdir(parents=True, exist_ok=True)
        self.db_path = db_path or str(data_dir / "demo.db")
        self._init_db()

    def _connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self) -> None:
        with self._connection() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sessions (
                    session_id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS results (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    session_id TEXT NOT NULL,
                    payload TEXT NOT NULL,
                    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS registry (
                    server TEXT NOT NULL,
                    version TEXT NOT NULL,
                    status TEXT NOT NULL,
                    notes TEXT,
                    updated_at TEXT NOT NULL,
                    PRIMARY KEY (server, version)
                )
                """
            )
            conn.commit()

    def ensure_session(self, session_id: str) -> None:
        with self._connection() as conn:
            conn.execute(
                "INSERT OR IGNORE INTO sessions(session_id, created_at) VALUES(?, ?)",
                (session_id, datetime.utcnow().isoformat()),
            )
            conn.commit()

    def append_event(self, event: EventRecord) -> None:
        self.ensure_session(event.session_id)
        with self._connection() as conn:
            conn.execute(
                "INSERT INTO events(session_id, payload) VALUES(?, ?)",
                (event.session_id, json.dumps(event.model_dump(mode="json"))),
            )
            conn.commit()

    def append_results(self, session_id: str, results: Iterable[TestResult]) -> None:
        with self._connection() as conn:
            for result in results:
                conn.execute(
                    "INSERT INTO results(session_id, payload) VALUES(?, ?)",
                    (session_id, json.dumps(result.model_dump(mode="json"))),
                )
            conn.commit()

    def record_registry_entries(self, entries: Iterable[RegistryEntry]) -> None:
        with self._connection() as conn:
            for entry in entries:
                conn.execute(
                    """
                    INSERT INTO registry(server, version, status, notes, updated_at)
                    VALUES(?, ?, ?, ?, ?)
                    ON CONFLICT(server, version) DO UPDATE SET
                        status=excluded.status,
                        notes=excluded.notes,
                        updated_at=excluded.updated_at
                    """,
                    (
                        entry.server,
                        entry.version,
                        entry.status,
                        entry.notes,
                        datetime.utcnow().isoformat(),
                    ),
                )
            conn.commit()

    def reset_registry(self, entries: Iterable[RegistryEntry]) -> None:
        with self._connection() as conn:
            conn.execute("DELETE FROM registry")
            conn.commit()
        self.record_registry_entries(entries)

    def update_registry_entry(self, entry: RegistryEntry) -> None:
        self.record_registry_entries([entry])

    def get_registry_snapshot(self) -> RegistrySnapshot:
        with self._connection() as conn:
            rows = conn.execute("SELECT * FROM registry").fetchall()
        entries = [
            RegistryEntry(
                server=row["server"],
                version=row["version"],
                status=row["status"],
                notes=row["notes"],
            )
            for row in rows
        ]
        return RegistrySnapshot(entries=entries, updated_at=datetime.utcnow())

    def get_session(self, session_id: str) -> SessionLog | None:
        with self._connection() as conn:
            session_row = conn.execute(
                "SELECT * FROM sessions WHERE session_id = ?", (session_id,)
            ).fetchone()
            if not session_row:
                return None
            event_rows = conn.execute(
                "SELECT payload FROM events WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()
            result_rows = conn.execute(
                "SELECT payload FROM results WHERE session_id = ? ORDER BY id ASC",
                (session_id,),
            ).fetchall()

        events = [EventRecord(**json.loads(row["payload"])) for row in event_rows]
        results = [TestResult(**json.loads(row["payload"])) for row in result_rows]

        return SessionLog(
            session_id=session_row["session_id"],
            created_at=datetime.fromisoformat(session_row["created_at"]),
            events=events,
            results=results,
        )
